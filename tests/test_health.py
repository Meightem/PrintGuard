import json

import pytest

from printguard.domain import (
    ClassificationState,
    ServiceSnapshot,
    ServiceStatus,
    StreamState,
)
from printguard.health import HealthStateStore, run_healthcheck


def test_health_store_writes_snapshot(tmp_path) -> None:
    health_path = tmp_path / "health.json"
    store = HealthStateStore(str(health_path))

    store.update(
        ServiceSnapshot(
            status=ServiceStatus.ONLINE,
            stream=StreamState.ON,
            classification=ClassificationState.SUCCESS,
            print_quality="9",
        ),
        inference_at=123.0,
    )

    payload = json.loads(health_path.read_text(encoding="utf-8"))
    assert payload["status"] == "online"
    assert payload["stream"] == "ON"
    assert payload["classification"] == "success"
    assert payload["last_inference_at"] == 123.0


def test_healthcheck_fails_when_stream_is_offline(tmp_path, monkeypatch) -> None:
    model_path = tmp_path / "model.onnx"
    options_path = tmp_path / "opt.json"
    prototypes_path = tmp_path / "prototypes.npz"
    health_path = tmp_path / "health.json"
    model_path.write_text("model", encoding="utf-8")
    options_path.write_text("{}", encoding="utf-8")
    prototypes_path.write_text("archive", encoding="utf-8")
    health_path.write_text(
        json.dumps(
            {
                "updated_at": 9999999999,
                "status": "offline",
                "stream": "OFF",
                "classification": "unknown",
                "print_quality": "unknown",
                "last_error": "stream offline",
                "last_inference_at": None,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("MODEL_PATH", str(model_path))
    monkeypatch.setenv("MODEL_OPTIONS_PATH", str(options_path))
    monkeypatch.setenv("PROTOTYPES_PATH", str(prototypes_path))
    monkeypatch.setenv("HEALTH_PATH", str(health_path))
    monkeypatch.setenv("HEALTH_STALE_AFTER_SECONDS", "180")

    with pytest.raises(SystemExit, match="stream offline"):
        run_healthcheck()
