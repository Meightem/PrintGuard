import json
import os
import time
from pathlib import Path

from .domain import ServiceSnapshot, ServiceStatus, StreamState


class HealthStateStore:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.last_error: str | None = None
        self.last_inference_at: float | None = None

    def update(
        self,
        snapshot: ServiceSnapshot,
        *,
        error: str | None = None,
        inference_at: float | None = None,
    ) -> None:
        if error is not None:
            self.last_error = error
        elif snapshot.status == ServiceStatus.ONLINE:
            self.last_error = None
        if inference_at is not None:
            self.last_inference_at = inference_at

        payload = {
            "updated_at": time.time(),
            "status": snapshot.status.value,
            "stream": snapshot.stream.value,
            "classification": snapshot.classification.value,
            "print_quality": snapshot.print_quality,
            "last_error": self.last_error,
            "last_inference_at": self.last_inference_at,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, separators=(",", ":"))
        os.replace(tmp_path, self.path)


def run_healthcheck() -> None:
    health_path = Path(os.getenv("HEALTH_PATH", "/tmp/printguard-health.json"))
    stale_after_seconds = int(os.getenv("HEALTH_STALE_AFTER_SECONDS", "180"))
    required_paths = [
        os.getenv("MODEL_PATH", "/opt/printguard/model/model.onnx"),
        os.getenv("MODEL_OPTIONS_PATH", "/opt/printguard/model/opt.json"),
        os.getenv("PROTOTYPES_PATH", "/opt/printguard/model/prototypes.npz"),
    ]
    for required_path in required_paths:
        if not required_path or not Path(required_path).exists():
            raise SystemExit(f"Missing required healthcheck path: {required_path}")
    if not health_path.exists():
        raise SystemExit(f"Health state file not found: {health_path}")

    with open(health_path, encoding="utf-8") as handle:
        payload = json.load(handle)

    updated_at = float(payload.get("updated_at", 0.0))
    if time.time() - updated_at > stale_after_seconds:
        raise SystemExit("Health state is stale")

    status = payload.get("status")
    stream = payload.get("stream")
    if status != ServiceStatus.ONLINE.value or stream != StreamState.ON.value:
        raise SystemExit(
            payload.get("last_error") or "PrintGuard service is not currently healthy"
        )
