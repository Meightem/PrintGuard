import signal

import printguard.main as main_module
from tests.helpers import make_settings


class FakeService:
    def __init__(self, _settings) -> None:
        self.stopped = False

    def run(self) -> None:
        raise main_module.ShutdownRequested()

    def stop(self) -> None:
        self.stopped = True


def test_run_stops_service_on_shutdown_requested(monkeypatch) -> None:
    service_holder: dict[str, FakeService] = {}
    registered_handlers: dict[int, object] = {}

    def build_service(settings) -> FakeService:
        service = FakeService(settings)
        service_holder["service"] = service
        return service

    monkeypatch.setattr(main_module.Settings, "from_env", lambda: make_settings())
    monkeypatch.setattr(main_module, "configure_logging", lambda _level: None)
    monkeypatch.setattr(main_module, "HeadlessService", build_service)
    monkeypatch.setattr(main_module.signal, "getsignal", lambda _signum: object())

    def record_signal_handler(signum: int, handler: object) -> None:
        registered_handlers[signum] = handler

    monkeypatch.setattr(main_module.signal, "signal", record_signal_handler)

    main_module.run()

    assert service_holder["service"].stopped is True
    assert signal.SIGINT in registered_handlers
    assert signal.SIGTERM in registered_handlers
