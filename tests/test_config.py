import json

import pytest

from printguard.config import Settings

SETTINGS_ENV_VARS = [
    "ADDON_OPTIONS_PATH",
    "MJPEG_URL",
    "MQTT_HOST",
    "MQTT_PORT",
    "MQTT_TOPIC_PREFIX",
    "MQTT_USERNAME",
    "MQTT_PASSWORD",
    "MQTT_CLIENT_ID",
    "MQTT_DISCOVERY_PREFIX",
    "MQTT_QOS",
    "MQTT_RETAIN_DISCOVERY",
    "MQTT_RETAIN_STATE",
    "MQTT_RETRY_DELAY_MS",
    "MQTT_CONNECT_TIMEOUT_SECONDS",
    "MQTT_CONNECT_MAX_ATTEMPTS",
    "MQTT_TLS_ENABLED",
    "MQTT_TLS_INSECURE",
    "MQTT_TLS_CA_PATH",
    "MQTT_TLS_CERTFILE",
    "MQTT_TLS_KEYFILE",
    "DEVICE_NAME",
    "DEVICE_ID",
    "DETECTION_INTERVAL_MS",
    "STREAM_OPEN_TIMEOUT_MS",
    "STREAM_RETRY_DELAY_MS",
    "STREAM_READ_FAILURE_LIMIT",
    "LOG_LEVEL",
    "MODEL_PATH",
    "MODEL_OPTIONS_PATH",
    "PROTOTYPES_PATH",
    "HEALTH_PATH",
    "HEALTH_STALE_AFTER_SECONDS",
]


def clear_settings_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in SETTINGS_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def test_from_env_prefers_environment_over_addon_options(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clear_settings_env(monkeypatch)
    options_path = tmp_path / "options.json"
    options_path.write_text(
        json.dumps(
            {
                "mjpeg_url": "http://addon.local/stream",
                "mqtt_host": "addon-mqtt",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ADDON_OPTIONS_PATH", str(options_path))
    monkeypatch.setenv("MJPEG_URL", "http://env.local/stream")
    monkeypatch.setenv("MQTT_HOST", "env-mqtt")

    settings = Settings.from_env()

    assert settings.mjpeg_url == "http://env.local/stream"
    assert settings.mqtt_host == "env-mqtt"


def test_from_env_reads_addon_options_and_normalizes_prefixes(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clear_settings_env(monkeypatch)
    options_path = tmp_path / "options.json"
    options_path.write_text(
        json.dumps(
            {
                "mjpeg_url": "http://addon.local/stream",
                "mqtt_host": "addon-mqtt",
                "mqtt_topic_prefix": "printguard/",
                "mqtt_discovery_prefix": "homeassistant/",
                "device_id": "test-device",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ADDON_OPTIONS_PATH", str(options_path))

    settings = Settings.from_env()

    assert settings.mqtt_topic_prefix == "printguard"
    assert settings.mqtt_discovery_prefix == "homeassistant"
    assert settings.mqtt_client_id == "test-device-client"


def test_from_env_requires_required_values(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_settings_env(monkeypatch)

    with pytest.raises(ValueError, match="MJPEG_URL is required"):
        Settings.from_env()

    monkeypatch.setenv("MJPEG_URL", "http://env.local/stream")

    with pytest.raises(ValueError, match="MQTT_HOST is required"):
        Settings.from_env()


def test_from_env_rejects_invalid_mqtt_qos(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_settings_env(monkeypatch)
    monkeypatch.setenv("MJPEG_URL", "http://env.local/stream")
    monkeypatch.setenv("MQTT_HOST", "env-mqtt")
    monkeypatch.setenv("MQTT_QOS", "3")

    with pytest.raises(ValueError, match="MQTT_QOS must be between 0 and 2"):
        Settings.from_env()


def test_from_env_requires_tls_cert_and_key_together(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_settings_env(monkeypatch)
    monkeypatch.setenv("MJPEG_URL", "http://env.local/stream")
    monkeypatch.setenv("MQTT_HOST", "env-mqtt")
    monkeypatch.setenv("MQTT_TLS_ENABLED", "true")
    monkeypatch.setenv("MQTT_TLS_CERTFILE", "/tmp/client.crt")

    with pytest.raises(
        ValueError,
        match="MQTT_TLS_CERTFILE and MQTT_TLS_KEYFILE must be set together",
    ):
        Settings.from_env()
