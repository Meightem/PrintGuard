import logging
import signal
from contextlib import suppress
from types import FrameType

from .config import Settings, configure_logging
from .runner import HeadlessService

LOGGER = logging.getLogger(__name__)


class ShutdownRequested(Exception):
    pass


def run() -> None:
    settings = Settings.from_env()
    configure_logging(settings.log_level)
    service = HeadlessService(settings)

    def handle_shutdown(_signum: int, _frame: FrameType | None) -> None:
        raise ShutdownRequested()

    previous_sigint = signal.getsignal(signal.SIGINT)
    previous_sigterm = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    try:
        service.run()
    except (KeyboardInterrupt, ShutdownRequested):
        service.stop()
    except Exception:
        LOGGER.exception("PrintGuard terminated with an unrecoverable error")
        with suppress(Exception):
            service.stop()
        raise
    finally:
        signal.signal(signal.SIGINT, previous_sigint)
        signal.signal(signal.SIGTERM, previous_sigterm)


if __name__ == "__main__":
    run()
