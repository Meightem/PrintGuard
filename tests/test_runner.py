import json
import logging
from typing import Unpack

import printguard.runner as runner_module
from printguard.domain import ClassificationState
from printguard.model import PredictionResult
from printguard.runner import HeadlessService
from tests.helpers import SettingsOverrides, make_settings


class FakeMQTTClient:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs
        self.messages: list[tuple[str, str | dict, bool]] = []
        self.connect_handlers: list[object] = []

    def add_connect_handler(self, handler: object) -> None:
        self.connect_handlers.append(handler)

    def publish(self, topic: str, payload: str | dict, retain: bool = True) -> None:
        self.messages.append((topic, payload, retain))

    def connect(self, availability_topic: str) -> None:
        self.availability_topic = availability_topic

    def wait_until_connected(self, timeout: float | None = None) -> bool:
        self.timeout = timeout
        return True

    def disconnect(self) -> None:
        self.disconnected = True


class FakeClassifier:
    def __init__(self, **_kwargs: object) -> None:
        self.loaded = False

    def load(self) -> None:
        self.loaded = True


def make_service(monkeypatch, **settings_overrides: Unpack[SettingsOverrides]):
    fake_mqtt = FakeMQTTClient()
    fake_classifier = FakeClassifier()
    monkeypatch.setattr(runner_module, "MQTTClient", lambda **kwargs: fake_mqtt)
    monkeypatch.setattr(
        runner_module,
        "ONNXClassifier",
        lambda **kwargs: fake_classifier,
    )
    service = HeadlessService(make_settings(**settings_overrides))
    return service, fake_mqtt


def test_publish_classification_requires_two_failure_votes(monkeypatch) -> None:
    service, _fake_mqtt = make_service(monkeypatch)
    prediction = PredictionResult(
        label="failure",
        classification_confidence=0.9,
        failure_confidence=0.9,
        margin=0.1,
        distances={},
    )

    service._publish_stream_online()
    service._publish_classification(prediction, inference_at=100.0)
    assert service.snapshot.classification == ClassificationState.SUCCESS

    service._publish_classification(prediction, inference_at=101.0)
    assert service.snapshot.classification == ClassificationState.FAILURE
    assert (
        service.state_publisher.last_published_state[service.topics.classification_state]
        == "failure"
    )


def test_publish_stream_error_updates_health_file(tmp_path, monkeypatch) -> None:
    service, _fake_mqtt = make_service(
        monkeypatch,
        health_path=str(tmp_path / "health.json"),
    )

    service._publish_stream_error("camera unavailable")

    payload = json.loads((tmp_path / "health.json").read_text(encoding="utf-8"))
    assert payload["status"] == "offline"
    assert payload["stream"] == "OFF"
    assert payload["last_error"] == "camera unavailable"


def test_publish_stream_error_logs_info_while_stream_is_already_offline(
    monkeypatch,
    caplog,
) -> None:
    service, _fake_mqtt = make_service(monkeypatch)

    with caplog.at_level(logging.DEBUG, logger="printguard.runner"):
        service._publish_stream_error("camera unavailable")

    assert "Stream unavailable: camera unavailable" in caplog.text
    assert not any(record.levelno >= logging.INFO for record in caplog.records)


def test_publish_stream_error_logs_warning_after_stream_was_online(
    monkeypatch,
    caplog,
) -> None:
    service, _fake_mqtt = make_service(monkeypatch)
    service._publish_stream_online()

    with caplog.at_level(logging.INFO, logger="printguard.runner"):
        service._publish_stream_error("camera disconnected")

    assert "Stream error: camera disconnected" in caplog.text
    assert any(record.levelno == logging.WARNING for record in caplog.records)
