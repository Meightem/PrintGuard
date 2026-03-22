# PrintGuard

PrintGuard is a Home Assistant add-on that reads one MJPEG webcam stream, runs the PrintGuard defect model on it, and publishes MQTT auto-discovery entities.

No web UI. No HACS integration. Just camera in, MQTT out.

## Install

1. Open the Add-on Store in Home Assistant.
2. Add this repository as a custom add-on repository:
   - `https://github.com/Meightem/PrintGuard`
3. Install `PrintGuard`.
4. Set at least:
   - `mjpeg_url`
   - `mqtt_host`
5. Start the add-on.

If you use the official Mosquitto add-on, `core-mosquitto` is usually the correct MQTT host.

## Main Options

- `mjpeg_url`: HTTP MJPEG stream URL
- `mqtt_host`: MQTT broker hostname
- `mqtt_port`: MQTT broker port
- `mqtt_topic_prefix`: state topic prefix, default `printguard`
- `mqtt_discovery_prefix`: Home Assistant discovery prefix, default `homeassistant`
- `mqtt_username`: optional MQTT username
- `mqtt_password`: optional MQTT password
- `mqtt_connect_timeout_seconds`: startup wait time for MQTT connection
- `mqtt_connect_max_attempts`: optional limit for initial MQTT connection retries, `0` means unlimited
- `mqtt_tls_enabled`: enable TLS for the MQTT connection
- `mqtt_tls_insecure`: allow insecure TLS validation for development-only setups
- `mqtt_tls_ca_path`: optional CA certificate path for TLS validation
- `mqtt_tls_certfile`: optional client certificate path for mutual TLS
- `mqtt_tls_keyfile`: optional client private key path for mutual TLS
- `device_id`: Home Assistant device identifier
- `device_name`: Home Assistant device name
- `detection_interval_ms`: time between inferences
- `stream_open_timeout_ms`: MJPEG connect timeout
- `stream_retry_delay_ms`: delay before reconnect attempts
- `stream_read_failure_limit`: consecutive failed frame reads before the stream is marked offline
- `mqtt_retry_delay_ms`: delay before MQTT reconnect attempts
- `log_level`: set `DEBUG` to log model details and exact MQTT payloads

## What Gets Created

The add-on publishes four main Home Assistant entities:

- `Classification`
- `Status`
- `Stream`
- `Print Quality`

`Print Quality` is a derived score from `1` to `10`, where `10` means the print looks great.

## Notes

- Classification is majority-vote confirmed, so one-frame flickers are filtered.
- Print Quality is derived from a temporally smoothed failure-confidence signal.
- Stable good-state MQTT updates are rate-limited; important changes still publish quickly.
- Stream availability is not the same thing as actual printer power state.
- The add-on image is pulled from GHCR and should match the version in `config.yaml`.
- This fork is heavily adapted from the original upstream project by Oliver Bravery.
- The runtime container now publishes a local health state file that is used by Docker health checks.
