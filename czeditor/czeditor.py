import concurrent.futures
import sys
import traceback
from ctypes import c_void_p
from time import perf_counter
from typing import *

import numpy as np
import sounddevice
from moviepy.video.VideoClip import VideoClip
from moviepy.audio.AudioClip import AudioClip
from PIL import Image
from PySide6.QtCore import QPoint, QSize, Qt, QTimerEvent
from PySide6.QtGui import (QImage, QKeyEvent, QMouseEvent, QPixmap,
                           QResizeEvent, QWheelEvent)
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import (QGraphicsScene, QGraphicsView, QLabel,
                               QMainWindow, QSizePolicy, QSplitter, QWidget)

from czeditor.base_ui import *
from czeditor.effectfunctions import *
from czeditor.sourcefunctions import *
from czeditor.keyframes import *
from czeditor.actionfunctions import *
from czeditor.ui import *
from czeditor.util import *
from czeditor.avreader import PyAVAudioWriter


# TODO : Move these into the Window class

def stateprocessor(frame, keyframes, windowClass):
    state = []
    for keyframe in keyframes:
        if keyframe.frame > frame:
            break
        state = keyframe.actOnKeyframes(state, windowClass)
    state = sorted(state, key=lambda k: k.layer)
    return state


def composite(state, parentclass):
    for keyframe in state:
        keyframe.composite(parentclass)


def frameprocessor(frame, keyframes):
    returnkeyframes = []
    for keyframe in keyframes:
        if keyframe.frame < frame:
            returnkeyframes.append(keyframe)
        else:
            return returnkeyframes


def getstate(i, windowClass):
    return stateprocessor(i, windowClass.keyframes, windowClass)


def getviewportimage(state, parentclass):
    composite(state, parentclass)


def getsound(state, sample):
    first = True
    buffer = np.zeros((512, 2))
    for keyframe in state:
        gotten = keyframe.getSound(sample)[0]
        if (len(gotten.shape) != 0):
            gotten = np.pad(
                gotten, ((0, 512-gotten.shape[0]), (0, 0)), "constant", constant_values=(0, 0))
            buffer += gotten
    return buffer

# mpyconfig.FFMPEG_BINARY = "ffmpeg"


rendered = None


class CzeVideoView(QOpenGLWidget):
    def __init__(self, windowObject, parent=None):
        # print(parentclass,parent)
        super().__init__(parent)
        self.state = []
        self.spectrum = np.zeros(512)
        self.windowObject = windowObject

    def initializeGL(self):

        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)
        # Generate a vertex buffer
        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        # Set geometry of the quad
        # glBufferData(GL_ARRAY_BUFFER,vertexes,GL_DYNAMIC_DRAW)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 20, c_void_p(0))
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 20, c_void_p(12))
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDepthFunc(GL_LEQUAL)

    def sizeHint(self):
        return QSize(1280, 720)
    # def resizeGL(self, w: int, h: int) -> None:
        # glViewport(-1280/2,-720/2,1280,720)
        # return super().resizeGL(1280, 720)

    def paintGL(self):
        global rendered

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glClearColor(0.1, 0.2, 0.2, 1.0)
        glLoadIdentity()

        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBindVertexArray(self.vao)
        # for keyframeId in range(len(self.state)):
        #    self.state[-keyframeId-1].composite(self.parentclass) # It is required to composite from end to beginning because OpenGL renders front-to-back rather than back-to-front
        projection = QMatrix4x4()
        # projection.frustum(-1280/32, 1280/32, 720/32, -720/32, 64, 131072)
        projection.perspective(
            self.windowObject.cameraParams.fov, 1280/720, 1, 32768)
        projection.rotate(QQuaternion.fromEulerAngles(self.windowObject.cameraParams.pitch,
                          self.windowObject.cameraParams.yaw, self.windowObject.cameraParams.roll))
        projection.translate(self.windowObject.cameraParams.x,
                             self.windowObject.cameraParams.y, self.windowObject.cameraParams.z)
        # print(projection)
        self.windowObject.rendering = True
        for keyframe in self.state:
            keyframe.composite(self.windowObject, self.spectrum, projection)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

        rendered = glReadPixels(
            0, 0, 1280, 720, GL_RGBA, GL_UNSIGNED_BYTE, None)
        self.windowObject.rendering = False


class CzeViewport(QWidget):
    def __init__(self, parent, parentclass):
        super().__init__(parent)
        self.videorenderer = CzeVideoView(parentclass, self)
        self.timestamp = 100
        self.scene = QGraphicsScene(self)
        self.graphicsview = QGraphicsViewEvent(self)
        self.graphicsview.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.graphicsview.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.graphicsview.horizontalScrollBar().disconnect(self.graphicsview)
        self.graphicsview.verticalScrollBar().disconnect(self.graphicsview)
        self.graphicsview.verticalScrollBar().setMaximum(200000000)
        self.graphicsview.horizontalScrollBar().setMaximum(200000000)
        self.graphicsview.setScene(self.scene)
        self.infolabel = QLabel(self)
        self.infolabel.raise_()
        self.infolabel.setStyleSheet("background: transparent;")
        self.parentclass = parentclass

        self.updateviewportimage(
            getstate(self.parentclass.playbackframe, self.parentclass), np.zeros(512))
        self.picture = QPixmap(1280, 720)
        # self.viewportimage = self.scene.addPixmap(QPixmap.fromImage(ImageQt.ImageQt(getviewportimage(self.timestamp,self.parentclass))))
        self.viewportimage = self.scene.addPixmap(self.picture)

        # self.thelayout = QHBoxLayout()
       # self.setLayout(self.thelayout)
        # self.setMaximumSize(1280,720)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)
        self.handles = []
        # self.startTimer(0.01,Qt.TimerType.PreciseTimer)
       # self.isplaying = False
        # self.somehandle = CzeViewportDraggableHandle(None,self,ParamLink(keyframes[0].params.compositing[0].params,"x"),ParamLink(keyframes[0].params.compositing[0].params,"y"))
        # self.scene.addItem(self.somehandle)
        self.graphicsview.onmove = self.mmoveEvent
        self.graphicsview.onscroll = self.scrollEvent
        self.vao = None
        self.vbo = None

    def sizeHint(self):
        return QSize(1280, 720)

    def updateviewportimage(self, state, spectrum):
        global rendered
        self.videorenderer.state = state
        self.videorenderer.spectrum = spectrum
        self.videorenderer.update()
        if (rendered):
            img = QImage(rendered, 1280, 720, QImage.Format_RGBA8888)
            self.picture = QPixmap.fromImage(img)
            # self.picture = self.picture.scaled(QSize(min(self.size().width(),1280),min(self.size().height(),720)),Qt.AspectRatioMode.KeepAspectRatio)
            self.viewportimage.setPixmap(self.picture)

    # self , keyframe of the handle , function of the param , param itself
    def createhandle(self, keyframe, function, param):
        # print(vars(function))
        if hasattr(function, "handle"):
            handles = function.handle(keyframe, self.parentclass, param)
            for handle in handles:
                self.handles.append(handle)
                self.scene.addItem(handle)

    def updatehandles(self):
        for handle in self.handles:
            self.scene.removeItem(handle)
        self.handles = []
        if (self.parentclass.selectedframe):
            self.createhandle(self.parentclass.selectedframe, self.parentclass.selectedframe.params.source.function(
            ), self.parentclass.selectedframe.params)
            for param in self.parentclass.selectedframe.params.effects:
                self.createhandle(
                    self.parentclass.selectedframe, param.function(), param)
            for param in self.parentclass.selectedframe.params.actions:
                self.createhandle(
                    self.parentclass.selectedframe, param.function(), param)

    def resizeEvent(self, event: QResizeEvent) -> None:
        self.updateviewportimage(
            getstate(self.parentclass.playbackframe, self.parentclass), np.zeros(512))
        self.graphicsview.setFixedSize(event.size())
        self.scene.setSceneRect(
            0, 0, self.picture.width()-2, self.picture.height()-2)
        r = self.graphicsview.sceneRect()
        r.setSize(self.size()/self.graphicsview.transform().m11()*1.25)
        self.graphicsview.setSceneRect(r)
        # size = event.size()
        # croppedevent = QResizeEvent(QSize(min(size.width(),size.height()/self.picture.size().width()*self.picture.size().height()),min(size.height(),size.width()/self.picture.size().height()*self.picture.size().width())),event.oldSize())
        return super().resizeEvent(event)

    def mmoveEvent(self, event: QMouseEvent, prevpos: QPoint) -> None:

        if event.buttons() & Qt.MouseButton.MiddleButton:
            self.graphicsview.setTransformationAnchor(
                QGraphicsView.ViewportAnchor.AnchorUnderMouse)
            delta = (event.pos()-prevpos) * \
                (self.graphicsview.sceneRect().width()/self.size().width())
            self.graphicsview.translate(delta.x(), delta.y())
            # self.graphicsview.setTransform(self.graphicsview.transform().translate(delta.x(),delta.y()))
        return super().mouseMoveEvent(event)

    def scrollEvent(self, event: QWheelEvent):
        """self.graphicsview.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        oldpos = self.graphicsview.mapToScene(event.position().toPoint())

        factor = 1.05
        scale = (factor if event.angleDelta().y() > 0 else 1/factor)
        self.graphicsview.scale(scale,scale)
        #self.graphicsview.setTransform(self.graphicsview.transform().translate(int((self.viewportimage.pos().x()-oldpos.x())*(scale-1)),int((self.viewportimage.pos().y()-oldpos.y())*(scale-1))))
        r = self.graphicsview.sceneRect()
        r.setSize(self.size()/self.graphicsview.transform().m11())
        self.graphicsview.setSceneRect(r)"""
        oldpos = self.graphicsview.mapToScene(event.position().toPoint())
        factor = 17/16
        self.graphicsview.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        self.graphicsview.scale((factor if event.angleDelta().y(
        ) > 0 else 1/factor), (factor if event.angleDelta().y() > 0 else 1/factor))
        r = self.graphicsview.sceneRect()
        r.setSize(self.size()/self.graphicsview.transform().m11()*factor)
        self.graphicsview.setSceneRect(r)
        newpos = self.graphicsview.mapToScene(event.position().toPoint())
        delta = newpos-oldpos
        self.graphicsview.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorViewCenter)

        self.graphicsview.translate(delta.x(), delta.y())
        self.showInfo(f"Scale: {round(self.graphicsview.transform().m11(),3)}")
        # self.viewportimage.setScale(self.viewportimage.scale()*scale)
        # thepos = QPoint(self.viewportimage.pos().x()+(self.viewportimage.pos().x()-oldpos.x())*(scale-1),self.viewportimage.pos().y()+(self.viewportimage.pos().y()-oldpos.y())*(scale-1))
        # self.viewportimage.setPos(thepos)
        # self.viewportimage.setTransformOriginPoint(self.viewportimage.scenePos())

    def showInfo(self, text):
        self.infolabel.setText(text)
        # self.infolabel.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)
        self.infolabel.setFixedSize(self.infolabel.sizeHint())

    # def paintEvent(self, event) -> None:
    #    painter = QPainter(self)
    #    painter.setViewport()
        # self.scene.render(painter,aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio)
        # return super().paintEvent(event)


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.playbackframe = 100
        self.sourcefunctionsdropdown = sourcefunctionsdropdown
        self.actionfunctionsdropdown = actionfunctionsdropdown
        self.effectfunctionsdropdown = effectfunctionsdropdown
        self.keyframes = Keyframelist(self)
        self.setWindowTitle("CZEditor")
        self.setGeometry(100, 100, 1280, 720)
        # button = QRedButton(self,"yeah",4,4,lambda: print("pressed"))
        self.setStyleSheet(
            "background-color: qradialgradient(spread:pad, cx:4.5, cy:4.5, radius:7, fx:4.5, fy:4.5, stop:0 rgba(255, 0, 0, 255), stop:1 rgba(0, 0, 0, 255));  color: rgb(255,192,192);")

        self.cameraParams = Params(
            {"x": -1280/2, "y": -720/2, "z": -360, "pitch": 0, "yaw": 0, "roll": 0, "fov": 90})
        hozsplitter = QSplitter(Qt.Orientation.Vertical, self)
        # rightsplitter = QSplitter(hozsplitter)
        topsplitter = QSplitter(hozsplitter)

        self.keyframeoptions = CzeKeyframeOptions(topsplitter, self)
        self.viewport = CzeViewport(topsplitter, self)
        self.presets = CzePresets(topsplitter, self)
        self.timeline = CzeTimeline(hozsplitter, self)

        self.selectedframe = None
        self.setCentralWidget(hozsplitter)
        self.show()

        self.draggedpreset = None
        self.startTimer(0.016, Qt.TimerType.CoarseTimer)
        self.lastframetime = perf_counter()
        self.isplaying = False
        self.starttime = perf_counter()
        self.startframe = self.playbackframe
        self.needtoupdate = True
        self.currentframestate = []
        # self.stream = self.pyaudio.open(format=self.pyaudio.get_format_from_width(1),channels=1,rate=48000,output=True)
        self.currentaudio = np.zeros(1024)
        sounddevice.default.samplerate = 48000
        sounddevice.default.channels = 1
        sounddevice.play(self.currentaudio)
        self.stream = sounddevice.OutputStream(
            channels=2, samplerate=48000, blocksize=512, callback=self.getnextsoundchunk)
        self.stream.start()
        self.playbacksample = int(self.playbackframe/60*48000)
        self.executor = concurrent.futures.ThreadPoolExecutor()
        self.seeking = False
        self.skipfuturesobject = None
        self.rendering = False
        self.currentspectrum = np.zeros(512)
        self.renderaudiobuffer = np.zeros(0)
        self.selectedAnimationFrame = None
        self.events = {}
        self.registerEvent("FrameUpdate")

    def registerEvent(self, event):
        self.events[event] = []

    def connectToEvent(self, event, function):
        self.events[event].append(function)

    def disconnectFromEvent(self, event, function):
        self.events[event].remove(function)

    def triggerEvent(self, event):
        for function in self.events[event]:
            function()

    def updateviewport(self):
        self.needtoupdate = True
        # self.viewport.update()

    def updatekeyframeoptions(self):
        self.keyframeoptions.update()

    def regeneratekeyframeoptions(self):
        self.keyframeoptions.regenerate()

    def getframeimage(self, i):
        i = i * 60
        self.playbackframe = i
        self.currentframestate = getstate(i, self)
        sound = getsound(self.currentframestate, int(i/60*48000))
        if (sound[32, 0] != self.currentaudio[512+32]):
            self.currentaudio[:512] = self.currentaudio[512:]
            self.currentaudio[512:] = sound[:, 0]
        self.currentspectrum = np.fft.rfft(self.currentaudio)
        self.currentspectrum = self.currentspectrum[:512]
        self.currentspectrum = np.abs(self.currentspectrum)
        self.viewport.updateviewportimage(
            self.currentframestate, self.currentspectrum)
        self.viewport.videorenderer.repaint()
        if rendered:
            resultimage = np.frombuffer(rendered, dtype=np.uint8)
            resultimage = np.reshape(resultimage, (720, 1280, 4))
            resultimage = resultimage[:, :, :3]
            resultimage = np.flip(resultimage, 0)
            return resultimage
        return np.zeros((1280, 720, 3))

    def getframesound(self):
        self.playbackframe = int(self.playbacksample/48000*60)
        self.currentframestate = getstate(self.playbackframe, self)
        returned = np.reshape(
            getsound(self.currentframestate, self.playbacksample)[:, 0], (1, 512))
        self.playbacksample += 512
        return returned

    def render(self, filename, length):
        self.playbacksample = 0
        self.renderaudiobuffer = np.zeros(0)
        clip = VideoClip(self.getframeimage, duration=length / 60)
        audiowriter = PyAVAudioWriter(self.getframesound, "_tempaudio.mp3")
        audiowriter.writeaudio(int(length/60*48000))
        # clip.write_videofile(filename=filename, fps=60, codec="libx264rgb", ffmpeg_params=["-strict","-2"]) perfection, doesnt embed | don't delete this
        clip.write_videofile(filename=filename, fps=60, codec="libvpx-vp9", ffmpeg_params=[
            "-pix_fmt", "yuv444p", "-crf", "25", "-b:v", "0"], write_logfile=True, audio="_tempaudio.mp3")  # perfection, embeds only on pc
        os.remove("_tempaudio.mp3")

    def keyPressEvent(self, event: QKeyEvent) -> None:
        # print(event.text())
        if event.text() == " ":
            self.isplaying = not self.isplaying
            self.starttime = perf_counter()
            self.startframe = self.playbackframe
        # elif event.text() == "r":
        #    self.render("renderedvideo.mp4",600)
        return super().keyPressEvent(event)

    def getnextsoundchunk(self, outdata, frames, time, status):
        if self.isplaying and not self.seeking:
            try:
                sound = getsound(self.currentframestate, self.playbacksample)
                if (sound[32, 0] != self.currentaudio[512+32]):
                    self.currentaudio[:512] = self.currentaudio[512:]
                    self.currentaudio[512:] = sound[:, 0]
                outdata[:] = sound

            except Exception:
                traceback.print_exc()
                self.currentaudio[:512] = self.currentaudio[512:]
                sound = np.zeros((512, 1))

                self.currentaudio[512:] = sound[:, 0]
                outdata[:] = sound
            self.playbacksample += 512
        else:
            self.currentaudio[:512] = self.currentaudio[512:]
            sound = np.zeros((512, 1))

            self.currentaudio[512:] = sound[:, 0]
            outdata[:] = sound
            self.playbacksample = int(self.playbackframe/60*48000)

    def seek(self, frame):
        # if self.skipfuturesobject is not None:
        #    self.skipfuturesobject.cancel()

        if (not self.isplaying and not self.seeking):
            self.skipfuturesobject = self.executor.submit(
                self.threadseek, frame)
        else:
            self.startframe = frame
            self.starttime = perf_counter()
            self.playbackframe = frame
            self.playbacksample = int(frame/60*48000)

    def threadseek(self, frame):

        self.seeking = True

        try:
            for keyframe in self.currentframestate:
                if hasattr(keyframe.params.source.function(), "seek"):
                    keyframe.params.source.function().seek(
                        keyframe.params.source.params, frame-keyframe.frame)
                for action in keyframe.params.actions:
                    if hasattr(action.function(), "seek"):
                        action.function().seek(action.params, frame-keyframe.frame)
                for effect in keyframe.params.effects:
                    if hasattr(effect.function(), "seek"):
                        effect.function().seek(effect.params, frame-keyframe.frame)
        except Exception:
            print("<ERROR DURING SEEKING>")
            traceback.print_exc()
            print("</ERROR DURING SEEKING>")
        self.startframe = frame
        self.starttime = perf_counter()
        self.playbackframe = frame
        self.playbacksample = int(frame/60*48000)
        self.currentframestate = getstate(self.playbackframe, self)
        self.seeking = False

    def timerEvent(self, event: QTimerEvent) -> None:

        if self.isplaying and not self.seeking:
            firstcopy = np.copy(self.currentaudio)

            self.currentspectrum = np.fft.rfft(firstcopy)
            # freq = np.fft.fftfreq(1)
            self.currentspectrum = self.currentspectrum[:512]
            self.currentspectrum = np.abs(self.currentspectrum)

            self.playbackframe = self.startframe + \
                int((perf_counter()-self.starttime)*60)
            # self.playbackframe += 1
            self.currentframestate = getstate(self.playbackframe, self)
            self.viewport.updateviewportimage(
                self.currentframestate, self.currentspectrum)
            self.timeline.updateplaybackcursor(self.playbackframe)
            self.triggerEvent("FrameUpdate")
            self.needtoupdate = False
        if self.needtoupdate and not self.seeking:
            self.viewport.updateviewportimage(
                getstate(self.playbackframe, self), self.currentspectrum)
            self.triggerEvent("FrameUpdate")
            self.needtoupdate = False
        return super().timerEvent(event)

    def showInfo(self, text):
        self.viewport.showInfo(text)

    def createKeyframe(self, keyframe: Keyframe):
        self.keyframes.add(keyframe)
        self.timeline.addKeyframe(keyframe)
        keyframe.initialize()

    def enterAnimationMode(self, property):
        self.timeline.enterAnimationMode(property)
