import av
import av.container
import czeditor.util.avhelper

import numpy as np

from PySide6.QtCore import QFileInfo


# PyAV video reader with intelligent seeking.
class PyAVSeekableVideoReader:

    def __init__(self, filename):
        self._filename = filename
        self._container: av.container.InputContainer = av.open(
            QFileInfo(self._filename).canonicalFilePath())
        self._stream = self._container.streams.video[0]
        self._currentFrame = 0
        self.frame_rate = float(self._stream.average_rate)
        self._keyframes = []
        self._container.streams.video[0].thread_type = "AUTO"
        self._stream.codec_context.skip_frame = "NONKEY"
        for frame in self._container.decode(self._stream):
            self._keyframes.append(
                int(frame.pts*self._stream.time_base*self.frame_rate))
        self._stream.codec_context.skip_frame = "DEFAULT"
        self._container.seek(0)
        theframe = next(self._container.decode(
            self._stream)).to_ndarray(format="rgb24")
        self._cachedFrame = np.full(
            (theframe.shape[0], theframe.shape[1], 4), 255, dtype=np.uint8)
        self._cachedFrame[:, :, :3] = theframe

    def seekForward(self, frame: int):
        self._currentFrame = frame
        for decodedFrame in self._container.decode(self._stream):
            if (int(decodedFrame.pts*self._stream.time_base*self.frame_rate) < frame):
                continue
            return decodedFrame
        else:
            return decodedFrame

    def seek(self, frame: int) -> av.VideoFrame:
        if (self._currentFrame == frame):
            return self._cachedFrame
        self._container.seek(
            int(frame/self._stream.time_base/self.frame_rate), stream=self._stream)
        return self.seekForward(frame)

    def __getitem__(self, frame: int):
        if (frame < self._currentFrame):
            self._cachedFrame[:, :, :3] = self.seek(
                frame).to_ndarray(format="rgb24")
        if (frame > self._currentFrame):
            for i in self._keyframes:
                if i < frame and i > self._currentFrame:
                    self._cachedFrame[:, :, :3] = self.seek(
                        frame).to_ndarray(format="rgb24")
                    break
                elif i > frame:
                    self._cachedFrame[:, :, :3] = self.seekForward(
                        frame).to_ndarray(format="rgb24")
                    break
            else:
                self._cachedFrame[:, :, :3] = self.seekForward(
                    frame).to_ndarray(format="rgb24")
        return self._cachedFrame

    def __len__(self):
        return self._stream.frames

    def close(self):
        self._container.close()


class PyAVAudioWriter:

    def __init__(self, nextsamples, filename):
        self._filename = filename
        self._samplefunction = nextsamples

    def writeaudio(self, samples):
        self._container = av.open(self._filename, "w")
        self._stream = self._container.add_stream("mp3", 48000)
        self._stream.channels = 1
        self._stream.sample_rate = 48000
        self._currentsample = 0
        while self._currentsample < samples:
            frame = av.AudioFrame.from_ndarray(np.ndarray.astype(
                self._samplefunction(), "<f8"), format="dbl", layout="mono")
            frame.sample_rate = 48000
            for packet in self._stream.encode(frame):
                self._container.mux(packet)
            self._currentsample += 512
        self._container.close()
