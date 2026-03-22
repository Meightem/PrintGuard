from .config import Settings, configure_logging
from .runner import HeadlessService


def run() -> None:
    settings = Settings.from_env()
    configure_logging(settings.log_level)
    service = HeadlessService(settings)
    try:
        service.run()
    except KeyboardInterrupt:
        service.stop()


if __name__ == "__main__":
    run()
