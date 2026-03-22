import json
import logging
import os
from dataclasses import dataclass

VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
TOPIC_WILDCARDS = {"#", "+"}


def _load_addon_options() -> dict:
    options_path = os.getenv("ADDON_OPTIONS_PATH", "/data/options.json")
    if not os.path.exists(options_path):
        return {}
    with open(options_path, encoding="utf-8") as handle:
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


def _require(name: str, value: str) -> None:
    if not value:
        raise ValueError(f"{name} is required")


def _require_positive(name: str, value: int) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")


def _require_non_negative(name: str, value: int) -> None:
    if value < 0:
        raise ValueError(f"{name} must be zero or greater")


def _require_range(name: str, value: int, minimum: int, maximum: int) -> None:
    if value < minimum or value > maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")


def _validate_topic_prefix(name: str, value: str) -> None:
    _require(name, value)
    if any(wildcard in value for wildcard in TOPIC_WILDCARDS):
        raise ValueError(f"{name} must not contain MQTT wildcards")


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

    def __post_init__(self) -> None:
        _require("MJPEG_URL", self.mjpeg_url)
        _require("MQTT_HOST", self.mqtt_host)
        _require("DEVICE_ID", self.device_id)
        _require("DEVICE_NAME", self.device_name)
        _validate_topic_prefix("MQTT_TOPIC_PREFIX", self.mqtt_topic_prefix)
        _validate_topic_prefix("MQTT_DISCOVERY_PREFIX", self.mqtt_discovery_prefix)
        _require_range("MQTT_PORT", self.mqtt_port, 1, 65535)
        _require_range("MQTT_QOS", self.mqtt_qos, 0, 2)
        _require_positive("MQTT_RETRY_DELAY_MS", self.mqtt_retry_delay_ms)
        _require_positive(
            "MQTT_CONNECT_TIMEOUT_SECONDS",
            self.mqtt_connect_timeout_seconds,
        )
        _require_non_negative(
            "MQTT_CONNECT_MAX_ATTEMPTS",
            self.mqtt_connect_max_attempts,
        )
        _require_positive("DETECTION_INTERVAL_MS", self.detection_interval_ms)
        _require_positive("STREAM_OPEN_TIMEOUT_MS", self.stream_open_timeout_ms)
        _require_positive("STREAM_RETRY_DELAY_MS", self.stream_retry_delay_ms)
        _require_positive("STREAM_READ_FAILURE_LIMIT", self.stream_read_failure_limit)
        _require("MODEL_PATH", self.model_path)
        _require("MODEL_OPTIONS_PATH", self.model_options_path)
        _require("PROTOTYPES_PATH", self.prototypes_path)
        _require("HEALTH_PATH", self.health_path)
        _require_positive(
            "HEALTH_STALE_AFTER_SECONDS",
            self.health_stale_after_seconds,
        )
        if self.log_level not in VALID_LOG_LEVELS:
            raise ValueError(
                "LOG_LEVEL must be one of: " + ", ".join(sorted(VALID_LOG_LEVELS))
            )
        if self.mqtt_tls_insecure and not self.mqtt_tls_enabled:
            raise ValueError(
                "MQTT_TLS_INSECURE requires MQTT_TLS_ENABLED to be true"
            )
        if bool(self.mqtt_tls_certfile) != bool(self.mqtt_tls_keyfile):
            raise ValueError(
                "MQTT_TLS_CERTFILE and MQTT_TLS_KEYFILE must be set together"
            )

    @classmethod
    def from_env(cls) -> "Settings":
        addon_options = _load_addon_options()
        mjpeg_url = _get_str("MJPEG_URL", addon_options)
        mqtt_host = _get_str("MQTT_HOST", addon_options)
        mqtt_topic_prefix = _get_str("MQTT_TOPIC_PREFIX", addon_options, "printguard")
        mqtt_discovery_prefix = _get_str(
            "MQTT_DISCOVERY_PREFIX",
            addon_options,
            "homeassistant",
        )
        device_id = _get_str("DEVICE_ID", addon_options, "printguard-mjpeg-1")
        return cls(
            mjpeg_url=mjpeg_url,
            mqtt_host=mqtt_host,
            mqtt_port=_get_int("MQTT_PORT", addon_options, 1883),
            mqtt_topic_prefix=mqtt_topic_prefix.rstrip("/"),
            mqtt_username=_get_str("MQTT_USERNAME", addon_options),
            mqtt_password=_get_str("MQTT_PASSWORD", addon_options),
            mqtt_client_id=_get_str(
                "MQTT_CLIENT_ID",
                addon_options,
                f"{device_id}-client",
            ),
            mqtt_discovery_prefix=mqtt_discovery_prefix.rstrip("/"),
            mqtt_qos=_get_int("MQTT_QOS", addon_options, 1),
            mqtt_retain_discovery=_get_bool(
                "MQTT_RETAIN_DISCOVERY",
                addon_options,
                True,
            ),
            mqtt_retain_state=_get_bool("MQTT_RETAIN_STATE", addon_options, True),
            mqtt_retry_delay_ms=_get_int("MQTT_RETRY_DELAY_MS", addon_options, 5000),
            mqtt_connect_timeout_seconds=_get_int(
                "MQTT_CONNECT_TIMEOUT_SECONDS",
                addon_options,
                30,
            ),
            mqtt_connect_max_attempts=_get_int(
                "MQTT_CONNECT_MAX_ATTEMPTS",
                addon_options,
                0,
            ),
            mqtt_tls_enabled=_get_bool("MQTT_TLS_ENABLED", addon_options, False),
            mqtt_tls_insecure=_get_bool("MQTT_TLS_INSECURE", addon_options, False),
            mqtt_tls_ca_path=_get_str("MQTT_TLS_CA_PATH", addon_options),
            mqtt_tls_certfile=_get_str("MQTT_TLS_CERTFILE", addon_options),
            mqtt_tls_keyfile=_get_str("MQTT_TLS_KEYFILE", addon_options),
            device_name=_get_str("DEVICE_NAME", addon_options, "PrintGuard MJPEG"),
            device_id=device_id,
            detection_interval_ms=_get_int(
                "DETECTION_INTERVAL_MS",
                addon_options,
                1000,
            ),
            stream_open_timeout_ms=_get_int(
                "STREAM_OPEN_TIMEOUT_MS",
                addon_options,
                5000,
            ),
            stream_retry_delay_ms=_get_int(
                "STREAM_RETRY_DELAY_MS",
                addon_options,
                5000,
            ),
            stream_read_failure_limit=_get_int(
                "STREAM_READ_FAILURE_LIMIT",
                addon_options,
                5,
            ),
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
                "/opt/printguard/model/prototypes.npz",
            ),
            health_path=_get_str(
                "HEALTH_PATH",
                addon_options,
                "/tmp/printguard-health.json",
            ),
            health_stale_after_seconds=_get_int(
                "HEALTH_STALE_AFTER_SECONDS",
                addon_options,
                180,
            ),
        )


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
