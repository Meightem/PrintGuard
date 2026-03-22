import json
import logging
import os
from dataclasses import dataclass


def _load_addon_options() -> dict:
    options_path = os.getenv("ADDON_OPTIONS_PATH", "/data/options.json")
    if not os.path.exists(options_path):
        return {}
    with open(options_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Add-on options file must contain an object: {options_path}")
    return data


def _get_raw(name: str, addon_options: dict, default=None):
    value = os.getenv(name)
    if value is not None:
        return value
    return addon_options.get(name.lower(), default)


def _get_bool(name: str, addon_options: dict, default: bool) -> bool:
    value = _get_raw(name, addon_options, default)
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, addon_options: dict, default: int) -> int:
    value = _get_raw(name, addon_options, default)
    if value is None or value == "":
        return default
    return int(value)


def _get_str(name: str, addon_options: dict, default: str = "") -> str:
    value = _get_raw(name, addon_options, default)
    if value is None:
        return default
    return str(value).strip()


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
    log_level: str
    model_path: str
    model_options_path: str
    prototypes_path: str

    @classmethod
    def from_env(cls) -> "Settings":
        addon_options = _load_addon_options()
        mjpeg_url = _get_str("MJPEG_URL", addon_options)
        mqtt_host = _get_str("MQTT_HOST", addon_options)
        mqtt_topic_prefix = _get_str("MQTT_TOPIC_PREFIX", addon_options, "printguard")
        if not mjpeg_url:
            raise ValueError("MJPEG_URL is required")
        if not mqtt_host:
            raise ValueError("MQTT_HOST is required")
        device_id = _get_str("DEVICE_ID", addon_options, "printguard-mjpeg-1")
        return cls(
            mjpeg_url=mjpeg_url,
            mqtt_host=mqtt_host,
            mqtt_port=_get_int("MQTT_PORT", addon_options, 1883),
            mqtt_topic_prefix=mqtt_topic_prefix.rstrip("/"),
            mqtt_username=_get_str("MQTT_USERNAME", addon_options),
            mqtt_password=_get_str("MQTT_PASSWORD", addon_options),
            mqtt_client_id=_get_str("MQTT_CLIENT_ID", addon_options, f"{device_id}-client"),
            mqtt_discovery_prefix=_get_str(
                "MQTT_DISCOVERY_PREFIX",
                addon_options,
                "homeassistant",
            ).rstrip("/"),
            mqtt_qos=_get_int("MQTT_QOS", addon_options, 1),
            mqtt_retain_discovery=_get_bool("MQTT_RETAIN_DISCOVERY", addon_options, True),
            mqtt_retain_state=_get_bool("MQTT_RETAIN_STATE", addon_options, True),
            mqtt_retry_delay_ms=_get_int("MQTT_RETRY_DELAY_MS", addon_options, 5000),
            device_name=_get_str("DEVICE_NAME", addon_options, "PrintGuard MJPEG"),
            device_id=device_id,
            detection_interval_ms=_get_int("DETECTION_INTERVAL_MS", addon_options, 1000),
            stream_open_timeout_ms=_get_int("STREAM_OPEN_TIMEOUT_MS", addon_options, 5000),
            stream_retry_delay_ms=_get_int("STREAM_RETRY_DELAY_MS", addon_options, 5000),
            log_level=_get_str("LOG_LEVEL", addon_options, "INFO").upper(),
            model_path=_get_str(
                "MODEL_PATH",
                addon_options,
                "/opt/printguard/model/model.onnx",
            ),
            model_options_path=_get_str(
                "MODEL_OPTIONS_PATH",
                addon_options,
                "/opt/printguard/model/opt.json",
            ),
            prototypes_path=_get_str(
                "PROTOTYPES_PATH",
                addon_options,
                "/opt/printguard/model/prototypes/cache/prototypes.pkl",
            ),
        )


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
