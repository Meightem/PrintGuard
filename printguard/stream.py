from urllib.parse import urlparse
from urllib.request import Request, urlopen

import cv2
import numpy as np


def create_frame_source(url: str, open_timeout_ms: int):
    scheme = urlparse(url).scheme.lower()
    if scheme in {"http", "https"}:
        return HTTPMJPEGStream(url, open_timeout_ms)
    return OpenCVFrameSource(url, open_timeout_ms)


class HTTPMJPEGStream:
    def __init__(self, url: str, open_timeout_ms: int):
        self.url = url
        self.timeout_seconds = open_timeout_ms / 1000.0
        self.response = None
        self.buffer = bytearray()

    def open(self) -> None:
        request = Request(self.url, headers={"User-Agent": "PrintGuard/1.0"})
        self.response = urlopen(request, timeout=self.timeout_seconds)

    def read_frame(self):
        if self.response is None:
            raise RuntimeError("MJPEG stream is not open")
        while True:
            start = self.buffer.find(b"\xff\xd8")
            if start != -1:
                end = self.buffer.find(b"\xff\xd9", start + 2)
                if end != -1:
                    jpeg_bytes = bytes(self.buffer[start : end + 2])
                    del self.buffer[: end + 2]
                    frame = cv2.imdecode(
                        np.frombuffer(jpeg_bytes, dtype=np.uint8),
                        cv2.IMREAD_COLOR,
                    )
                    if frame is not None:
                        return frame
            try:
                chunk = self.response.read(4096)
            except TimeoutError as exc:
                raise RuntimeError("Timed out reading MJPEG stream") from exc
            if not chunk:
                raise RuntimeError("MJPEG stream ended")
            self.buffer.extend(chunk)
            self._trim_buffer()

    def close(self) -> None:
        if self.response is not None:
            self.response.close()
            self.response = None
        self.buffer.clear()

    def _trim_buffer(self) -> None:
        max_buffer_size = 4 * 1024 * 1024
        if len(self.buffer) <= max_buffer_size:
            return
        start = self.buffer.rfind(b"\xff\xd8")
        if start > 0:
            del self.buffer[:start]
        else:
            del self.buffer[:-1024]


class OpenCVFrameSource:
    def __init__(self, url: str, open_timeout_ms: int):
        self.url = url
        self.open_timeout_ms = open_timeout_ms
        self.cap: cv2.VideoCapture | None = None

    def open(self) -> None:
        cap = cv2.VideoCapture(self.url, cv2.CAP_ANY)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, self.open_timeout_ms)
        if not cap.isOpened():
            raise RuntimeError("Failed to open video stream")
        self.cap = cap

    def read_frame(self):
        if self.cap is None:
            raise RuntimeError("Video stream is not open")
        ok, frame = self.cap.read()
        if not ok or frame is None:
            return None
        return frame

    def close(self) -> None:
        if self.cap is not None:
            self.cap.release()
            self.cap = None
