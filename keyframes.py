from typing import overload
from util import *
import numpy as np
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram,compileShader
from PySide6.QtGui import QMatrix4x4
from ctypes import c_void_p
from openglfunctions import *
#
# Image, Vertices, Fragment Shader, Vertex Shader
#
# [["uniform float time"],["""pos = pos+sin(pos*9+time/70);""","""pos = pos+time/90;\npos = mod(pos,1);"""],["""color=color*2;"""]]
#
##version 450 core
#in vec2 vertexColor;
#...
#out vec4 color;
#void main()
#{
#    vec2 pos = vertexColor;
#    //
#    pos = pos+sin(pos*9);
#    pos = pos+time/90;
#    float beat = sin(time/);
#    pos = mod(pos,1);
#    //
#    color = texture(image,pos);
#    //
#    color = color*2;
#    //
#}
#
class Keyframe():
    def __init__(self, frame, param:Params):
        self.frame = frame
        self.params = param
        self.imageparams = param.image
        self.stateparams = param.states
        self.compositingparams = param.compositing
        self.shared = Params({})
        self.lastShaderList = None
        self.compiledPrograms = None
        #self.compiledShaders = None  # TODO : Somehow delete programs without deleting shaders.
        self.currentTextureSize = None
        self.currentTexture = None
        self.fbo = None
    def image(self,parentclass): # TODO : Rename this to source
        return self.params.image.function().image(self.imageparams.params,parentclass,parentclass.playbackframe-self.frame)
    
    def state(self, statetomodify,windowClass): #action
        for stateparam in self.stateparams:
            statetomodify = stateparam.function().state(statetomodify,self,stateparam,windowClass.playbackframe-self.frame)
        return statetomodify
    
    def composite(self,windowObject):

        if(not hasattr(self.params.image.function(),"image")):
            return
        image = self.image(windowObject)
        imageDataPointer = image.ctypes.data
        vertices = np.empty((0,5),dtype=np.float32)
        shader = []

        for compositingparam in self.compositingparams:
            if hasattr(compositingparam.function(),"composite"):
                image,vertices,shader = compositingparam.function().composite(image,vertices,shader,compositingparam.params,windowObject,self,windowObject.playbackframe-self.frame)
        if(not shader):
            return
        vertices = vertices.flatten()

        newPassIndexes = []
        for i in range(len(shader)):
            if(shader[i][4]):
                newPassIndexes.append(i+1)
        if(self.fbo is None):
            self.fbo = glGenFramebuffers(1)
        #glBindFramebuffer(GL_FRAMEBUFFER,self.fbo)

        if(str(shader) != str(self.lastShaderList)):
            self.lastShaderList = shader
            #if(self.compiledPrograms):
                #for compiledShader in self.compiledShaders:
                #    if(glIsShader(compiledShader)):
                #        glDeleteShader(compiledShader)
                #        print(f"DELETING SHADER {compiledShader}")
                #for program in self.compiledPrograms:
                #    glDeleteProgram(program)
                #    print(f"DELETING PROGRAM {program}")
            self.compiledPrograms = []
            self.compiledShaders = []
            shadersnippet = []
            i = 0
            for snippet in shader:
                shadersnippet.append(snippet)
                if(snippet[4] and i != len(shader)-1):
                    shaderslist = GenerateShader(shadersnippet,True)
                    #self.compiledShaders += shaderslist
                    #print(shadersnippet)
                    #print(f"SHADERS LIST {shaderslist}")
                    self.compiledPrograms.append(compileProgram(*shaderslist))
                    shadersnippet = []
                elif(i == len(shader)-1):
                    shaderslist = GenerateShader(shadersnippet,False)
                    #self.compiledShaders += shaderslist
                    #print(f"SHADERS LIST {shaderslist}")
                    #print(shadersnippet)
                    #print(shaderslist)
                    self.compiledPrograms.append(compileProgram(*shaderslist))
                i+=1
            #print("recompiled")
            

        if(self.currentTexture == None):
            self.currentTexture = glGenTextures(1)
            self.currentTextureSize = (0,0)
        
        glBindTexture(GL_TEXTURE_2D,self.currentTexture)

        if(self.currentTextureSize[0] != image.shape[1] or self.currentTextureSize[1] != image.shape[0]):

            if(self.fbo):
                glDeleteFramebuffers(1,[self.fbo])

            self.fbo = glGenFramebuffers(1)
            glBindFramebuffer(GL_FRAMEBUFFER,self.fbo)

            glPixelStorei(GL_UNPACK_ALIGNMENT,1)

            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST)
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST)
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_BORDER)
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_BORDER)
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_BASE_LEVEL,0)
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAX_LEVEL,0)

            glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,image.shape[1],image.shape[0],0,GL_RGBA,GL_UNSIGNED_BYTE,c_void_p(imageDataPointer))
            self.currentTextureSize = (image.shape[1],image.shape[0])

            glFramebufferTexture(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,self.currentTexture,0)
            
            glDrawBuffers(1,[GL_COLOR_ATTACHMENT0])
            glBindFramebuffer(GL_FRAMEBUFFER,0)
        glTexSubImage2D(GL_TEXTURE_2D,0,0,0,image.shape[1],image.shape[0],GL_RGBA,GL_UNSIGNED_BYTE,c_void_p(imageDataPointer))
        if(len(self.compiledPrograms)>1):
            glBindFramebuffer(GL_FRAMEBUFFER,self.fbo)
            glViewport(0,0,image.shape[1],image.shape[0])
            #glClear(GL_COLOR_BUFFER_BIT)
            #glClearColor(0.0,0.0,0.0,0.0)
            glDisable(GL_DEPTH_TEST)
            glBufferData(GL_ARRAY_BUFFER,np.array([[-1,-1, 0.0, 0.0, 0.0],
            [1,  -1, 0.0, 1.0, 0.0],
            [1,  1, 0.0, 1.0, 1.0],
            [-1,  -1, 0.0, 0.0, 0.0],
            [-1,  1, 0.0, 0.0, 1.0],
            [1,  1, 0.0, 1.0, 1.0]],dtype=np.float32),GL_DYNAMIC_DRAW)
            
            for program in self.compiledPrograms[:-1]:
                
                glUseProgram(program)
                glUniform1i(glGetUniformLocation(program,"image"),0)
                glUniform1f(glGetUniformLocation(program,"frame"),windowObject.playbackframe-self.frame)
                glActiveTexture(GL_TEXTURE0)
                glDrawArrays(GL_TRIANGLES,0,6)

            glBindFramebuffer(GL_FRAMEBUFFER,1) # WHAT
            glEnable(GL_DEPTH_TEST)            
            glViewport(0,0,1280,720)
        
        glBufferData(GL_ARRAY_BUFFER,np.array(vertices,dtype=np.float32),GL_DYNAMIC_DRAW)
        
        #print(self.compiledPrograms)
        glUseProgram(self.compiledPrograms[-1])

        projection = QMatrix4x4()
        projection.frustum(-1280/32,1280/32,720/32,-720/32,64,4096)
        projection.translate(-1280/2,-720/2,-1024)
        glUniformMatrix4fv(glGetUniformLocation(self.compiledPrograms[-1],"matrix"),1,GL_FALSE,np.array(projection.data(),dtype=np.float32))

        glUniform1i(glGetUniformLocation(self.compiledPrograms[-1],"image"),0)

        glUniform1f(glGetUniformLocation(self.compiledPrograms[-1],"frame"),windowObject.playbackframe-self.frame)

        glActiveTexture(GL_TEXTURE0)
        glDrawArrays(GL_TRIANGLES,0,int(vertices.shape[0]/5))

        glBindTexture(GL_TEXTURE_2D,0)
        glUseProgram(0) # Hack

    def sound(self,sample):
        if hasattr(self.imageparams.function(),"sound"):
            source = self.imageparams.function().sound(self.imageparams.params,sample-int(self.frame/60*48000))
            for soundeffectparam in self.compositingparams:
                if hasattr(soundeffectparam.function(),"soundeffect"):
                    source = soundeffectparam.function().soundeffect(source,soundeffectparam,sample-int(self.frame/60*48000))
            return source
        return np.zeros((1024,2)),48000

    def timelineitems(self):
        items = []
        for action in self.params.states:
            if hasattr(action.function(),"timelineitem"):
                items.append(action.function().timelineitem(action.params,self))
        for effect in self.params.compositing:
            if hasattr(effect.function(),"timelineitem"):
                items.append(effect.function().timelineitem(effect.params,self))
        return items
        
class Keyframelist():
    def __init__(self,windowClass):
        self.windowClass = windowClass
        self.keyframes = []
        self.needssorting = False
    def add(self,keyframe:Keyframe) -> None:
        self.keyframes.append(keyframe)
        self.needssorting = True
    def append(self,keyframe:Keyframe) -> None:
        self.keyframes.append(keyframe)
        self.needssorting = True
    @overload
    def change(self,keyframe:Keyframe,change:Keyframe) -> None:
        ...
    @overload
    def change(self,i:int,change:Keyframe) -> None:
        ...
    def change(self,o,change:Keyframe) -> None:
        if isinstance(o,Keyframe):
            i = self.keyframes.index(o)
        else:
            i = o
        prevframe = self.keyframes[i].frame
        self.keyframes[i] = change
        self.needssorting = True
    @overload
    def remove(self,keyframe:Keyframe) -> None:
        ...
    @overload
    def remove(self,i:int) -> None:
        ...
    def remove(self,o) -> None:
        if isinstance(o,Keyframe):
            i = self.keyframes.index(o)
        else:
            i = o
        self.keyframes.pop(i)
    def pop(self,i:int) -> None:
        self.keyframes.pop(i)
    def len(self) -> int:
        return len(self.keyframes)
    def get(self,i) -> Keyframe:
        if self.needssorting:
            self.keyframes = sorted(self.keyframes,key=lambda k: k.frame)
            self.needssorting = False
        return self.keyframes[i]
    def __str__(self) -> str:
        if self.needssorting:
            self.keyframes = sorted(self.keyframes,key=lambda k: k.frame)
            self.needssorting = False
        return str(self.keyframes)
    def __getitem__(self,i:int) -> Keyframe:
        if self.needssorting:
            self.keyframes = sorted(self.keyframes,key=lambda k: k.frame)
            self.needssorting = False
        return self.keyframes[i]
    def __setitem__(self,i:int,change:Keyframe) -> None:
        prevframe = self.keyframes[i].frame
        self.keyframes[i] = change
        self.needssorting = True
    @overload
    def setframe(self,keyframe:Keyframe,frame:int):
        ...
    @overload
    def setframe(self,i:int,frame:int):
        ...
    def setframe(self,o,frame:int):
        if isinstance(o,Keyframe):
            i = self.keyframes.index(o)
        else:
            i = o
        prevframe = self.keyframes[i].frame
        self.keyframes[i].frame = frame
        self.needssorting = True
    def isinrange(self,i) -> bool:
        return len(self.keyframes) > i and i > 0
    def getsafe(self,i):
        if len(self.keyframes) > i and i > 0:
            return self.keyframes[i]
        else:
            return None
    def isin(self,keyframe:Keyframe) -> bool:
        return keyframe in self.keyframes
    def create(self,frame:int):
        addedkeyframe = Keyframe(frame,Params(
            {
                "image":
                {
                    "function":Selectable(0,self.windowClass.imagefunctionsdropdown),
                    "params":Selectable(0,self.windowClass.imagefunctionsdropdown)().params.copy()
                },
                "states":[],
                "compositing":[]
            }
        ))
        self.append(addedkeyframe)
        
        return addedkeyframe

"""keyframes.append(Keyframe(20,Params(
    {
        "image":
        {
            "function":Selectable(0,imagefunctionsdropdown),
            "params":{"imagepath":FileProperty("editor/icondark.png")}
        },
        "states":
        [
            {
                "function":Selectable(0,statefunctionsdropdown),
                "params":{}
            }
        ],
        "compositing":
        [
            {
                "function":Selectable(1,compositingfunctionsdropdown),
                "params":
                {
                    "x":IntProperty(0),
                    "y":IntProperty(0),
                    "z":IntProperty(0),
                    "width":IntProperty(1280),
                    "height":IntProperty(720),
                    "Xrotation":IntProperty(0),
                    "Yrotation":IntProperty(0),
                    "Zrotation":IntProperty(0),
                    "relativewidth":IntProperty(100),
                    "relativeheight":IntProperty(100),
                    "textureid":0,
                    "vbo":0,
                    "vao":0,
                    "pbo":0,
                    "lastsize":(32,32)

                }
            }
        ]
    })))"""
"""keyframes.append(Keyframe(40,Params(
    {
        "image":
        {
            "function":Selectable(0,imagefunctionsdropdown),
            "params":{"imagepath":"xp/Close button Active.png"}
        },
        "states":
        [
            {
                "function":Selectable(0,statefunctionsdropdown),
                "params":{}
            }
        ],
        "compositing":
        [
            {
                "function":Selectable(0,compositingfunctionsdropdown),
                "params":
                {
                    "x":500,
                    "y":400,
                }
            }
        ]
    })))
keyframes.append(Keyframe(60,Params(
    {
        "image":
        {
            "function":Selectable(0,imagefunctionsdropdown),
            "params":{"imagepath":"xp/Information.png"}
        },
        "states":
        [
            {
                "function":Selectable(0,statefunctionsdropdown),
                "params":{}
            }
        ],
        "compositing":
        [
            {
                "function":Selectable(0,compositingfunctionsdropdown),
                "params":
                {
                    "x":500,
                    "y":400,
                }
            }
        ]
    })))
keyframes.append(Keyframe(80,Params(
    {
        "image":
        {
            "function":Selectable(0,imagefunctionsdropdown),
            "params":{"imagepath":"xp/Exclamation.png"}
        },
        "states":
        [
            {
                "function":Selectable(0,statefunctionsdropdown),
                "params":{}
            }
        ],
        "compositing":
        [
            {
                "function":Selectable(0,compositingfunctionsdropdown),
                "params":
                {
                    "x":500,
                    "y":400,
                }
            }
        ]
    })))"""
#keyframes.append(Keyframe(10, Params({"image":{"function":Selectable(1,imagefunctionsdropdown),"params":{"text":"smoke","buttons":["yeah","lets go","Cancel"]}},"states":[{"function":Selectable(0,statefunctionsdropdown),"params":{}}],"compositing":[{"function":Selectable(0,compositingfunctionsdropdown),"params":{"x":100,"y":200}}]})))
#keyframes.append(Keyframe(70, Params({"image":{"function":Selectable(1,imagefunctionsdropdown),"params":{"text":"gdfgjdlgrgrelhjrtklhjgreg","buttons":["OK"]}},"states":[{"function":Selectable(0,statefunctionsdropdown),"params":{}}],"compositing":[{"function":Selectable(0,compositingfunctionsdropdown),"params":{"x":120,"y":220}}]})))
#keyframes.append(Keyframe(130, Params({"image":{"function":Selectable(1,imagefunctionsdropdown),"params":{"title":"Error","erroricon":Selectable(1,[["Critical Error","xp/Critical Error.png"],["Exclamation","xp/Exclamation.png"],["Information","xp/Information.png"],["Question","xp/Question.png"],["None",""]]),"buttons":["Yes","No"]}},"states":[{"function":Selectable(0,statefunctionsdropdown),"params":{}}],"compositing":[{"function":Selectable(0,compositingfunctionsdropdown),"params":{"x":140,"y":240}}]})))
