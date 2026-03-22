from printguard.stream import HTTPMJPEGStream, OpenCVFrameSource, create_frame_source


def test_create_frame_source_returns_http_stream_for_http_urls() -> None:
    source = create_frame_source("http://printer.local/stream", 1000)

    assert isinstance(source, HTTPMJPEGStream)


def test_create_frame_source_returns_opencv_source_for_non_http_urls() -> None:
    source = create_frame_source("rtsp://printer.local/stream", 1000)

    assert isinstance(source, OpenCVFrameSource)
