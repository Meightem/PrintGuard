from dataclasses import replace
from typing import TypedDict, Unpack

from printguard.config import Settings


class SettingsOverrides(TypedDict, total=False):
    mjpeg_url: str
    mqtt_host: str
    mqtt_port: int
    mqtt_topic_prefix: str
    mqtt_username: str
    mqtt_password: str
    mqtt_client_id: str
    mqtt_discovery_prefix: str
    mqtt_qos: int
    mqtt_retain_discovery: bool
    mqtt_retain_state: bool
    mqtt_retry_delay_ms: int
    mqtt_connect_timeout_seconds: int
    mqtt_connect_max_attempts: int
    mqtt_tls_enabled: bool
    mqtt_tls_insecure: bool
    mqtt_tls_ca_path: str
    mqtt_tls_certfile: str
    mqtt_tls_keyfile: str
    device_name: str
    device_id: str
    detection_interval_ms: int
    stream_open_timeout_ms: int
    stream_retry_delay_ms: int
    stream_read_failure_limit: int
    log_level: str
    model_path: str
    model_options_path: str
    prototypes_path: str
    health_path: str
    health_stale_after_seconds: int


def make_settings(**overrides: Unpack[SettingsOverrides]) -> Settings:
    base = Settings(
        mjpeg_url="http://printer.local:8080/?action=stream",
        mqtt_host="mqtt.local",
        mqtt_port=1883,
        mqtt_topic_prefix="printguard",
        mqtt_username="",
        mqtt_password="",
        mqtt_client_id="printguard-mjpeg-1-client",
        mqtt_discovery_prefix="homeassistant",
        mqtt_qos=1,
        mqtt_retain_discovery=True,
        mqtt_retain_state=True,
        mqtt_retry_delay_ms=5000,
        mqtt_connect_timeout_seconds=30,
        mqtt_connect_max_attempts=0,
        mqtt_tls_enabled=False,
        mqtt_tls_insecure=False,
        mqtt_tls_ca_path="",
        mqtt_tls_certfile="",
        mqtt_tls_keyfile="",
        device_name="PrintGuard MJPEG",
        device_id="printguard-mjpeg-1",
        detection_interval_ms=1000,
        stream_open_timeout_ms=5000,
        stream_retry_delay_ms=5000,
        stream_read_failure_limit=5,
        log_level="INFO",
        model_path="/opt/printguard/model/model.onnx",
        model_options_path="/opt/printguard/model/opt.json",
        prototypes_path="/opt/printguard/model/prototypes.npz",
        health_path="/tmp/printguard-health.json",
        health_stale_after_seconds=180,
    )
    return replace(base, **overrides)
