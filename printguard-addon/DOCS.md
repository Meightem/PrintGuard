# PrintGuard

PrintGuard reads one MJPEG stream, classifies frames with the baked-in ONNX model, and publishes Home Assistant compatible MQTT discovery and state topics.

## Install

1. In Home Assistant, open the Add-on Store.
2. Add this repository URL as a custom repository: `https://github.com/Meightem/PrintGuard`
3. Install `PrintGuard`.
4. Fill in at least:
   - `mjpeg_url`
   - `mqtt_host`
5. Start the add-on.

## Recommended MQTT Host

- If you use the official Mosquitto add-on, try `core-mosquitto`.
- If you use an external broker, enter its hostname or IP address.

## Main Options

- `mjpeg_url`: HTTP MJPEG stream URL
- `mqtt_host`: MQTT broker hostname
- `mqtt_port`: MQTT broker port
- `mqtt_topic_prefix`: state topic prefix, default `printguard`
- `mqtt_discovery_prefix`: Home Assistant discovery prefix, default `homeassistant`
- `mqtt_username`: optional MQTT username
- `mqtt_password`: optional MQTT password
- `device_id`: Home Assistant device identifier
- `device_name`: Home Assistant device name
- `detection_interval_ms`: time between inferences
- `stream_open_timeout_ms`: MJPEG connect timeout
- `stream_retry_delay_ms`: delay before reconnect attempts
- `mqtt_retry_delay_ms`: delay before MQTT reconnect attempts
- `enabled`: initial enabled state
- `log_level`: use `DEBUG` to log model outputs and exact MQTT publishes

## Notes

- This add-on does not expose a web UI.
- Stream availability is reported over MQTT; it is not a direct printer power signal.
- MQTT discovery is automatic, so no custom HACS integration is required.
- The add-on publishes extra classification telemetry including classification confidence, failure confidence, and a derived severity state.
- The add-on image is pulled from GHCR and should match the version in `config.yaml`.
