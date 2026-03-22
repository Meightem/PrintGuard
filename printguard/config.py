import logging
import os
from dataclasses import dataclass


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


def _get_str(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip()


@dataclass(frozen=True)
class Settings:
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
    device_name: str
    device_id: str
    detection_interval_ms: int
    stream_open_timeout_ms: int
    stream_retry_delay_ms: int
    enabled: bool
    log_level: str
    model_path: str
    model_options_path: str
    prototypes_path: str

    @classmethod
    def from_env(cls) -> "Settings":
        mjpeg_url = _get_str("MJPEG_URL")
        mqtt_host = _get_str("MQTT_HOST")
        mqtt_topic_prefix = _get_str("MQTT_TOPIC_PREFIX", "printguard")
        if not mjpeg_url:
            raise ValueError("MJPEG_URL is required")
        if not mqtt_host:
            raise ValueError("MQTT_HOST is required")
        device_id = _get_str("DEVICE_ID", "printguard-mjpeg-1")
        return cls(
            mjpeg_url=mjpeg_url,
            mqtt_host=mqtt_host,
            mqtt_port=_get_int("MQTT_PORT", 1883),
            mqtt_topic_prefix=mqtt_topic_prefix.rstrip("/"),
            mqtt_username=_get_str("MQTT_USERNAME"),
            mqtt_password=_get_str("MQTT_PASSWORD"),
            mqtt_client_id=_get_str("MQTT_CLIENT_ID", f"{device_id}-client"),
            mqtt_discovery_prefix=_get_str("MQTT_DISCOVERY_PREFIX", "homeassistant").rstrip("/"),
            mqtt_qos=_get_int("MQTT_QOS", 1),
            mqtt_retain_discovery=_get_bool("MQTT_RETAIN_DISCOVERY", True),
            mqtt_retain_state=_get_bool("MQTT_RETAIN_STATE", True),
            mqtt_retry_delay_ms=_get_int("MQTT_RETRY_DELAY_MS", 5000),
            device_name=_get_str("DEVICE_NAME", "PrintGuard MJPEG"),
            device_id=device_id,
            detection_interval_ms=_get_int("DETECTION_INTERVAL_MS", 1000),
            stream_open_timeout_ms=_get_int("STREAM_OPEN_TIMEOUT_MS", 5000),
            stream_retry_delay_ms=_get_int("STREAM_RETRY_DELAY_MS", 5000),
            enabled=_get_bool("ENABLED", True),
            log_level=_get_str("LOG_LEVEL", "INFO").upper(),
            model_path=_get_str("MODEL_PATH", "/opt/printguard/model/model.onnx"),
            model_options_path=_get_str("MODEL_OPTIONS_PATH", "/opt/printguard/model/opt.json"),
            prototypes_path=_get_str(
                "PROTOTYPES_PATH",
                "/opt/printguard/model/prototypes/cache/prototypes.pkl",
            ),
        )


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
