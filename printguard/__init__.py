"""PrintGuard headless MJPEG to MQTT service."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("printguard")
except PackageNotFoundError:  # pragma: no cover - fallback for local execution
    __version__ = "0.3.4"
