# PrintGuard Headless MQTT Usage

This document describes the new headless runtime that reads one MJPEG stream,
runs ONNX inference, and publishes Home Assistant-compatible MQTT topics.

## What It Does

The headless service:

- reads one `MJPEG_URL`
- loads a baked-in ONNX model from the container image
- publishes Home Assistant MQTT Discovery entities on startup
- publishes stream availability, service state, last error, and classification
- retries automatically when the stream becomes unavailable

It does not expose HTTP endpoints, a web UI, SSE, notifications, or printer APIs.

## Build

Build the headless image with:

```bash
docker build -f Dockerfile.headless -t printguard-headless:local .
```

The model artifacts are downloaded during image build and baked into the image at:

- `/opt/printguard/model/model.onnx`
- `/opt/printguard/model/opt.json`
- `/opt/printguard/model/prototypes/cache/prototypes.pkl`

## Run

Example runtime command:

```bash
docker run --rm \
  -e MJPEG_URL="http://printer.local:8080/?action=stream" \
  -e MQTT_HOST="mqtt.local" \
  -e MQTT_PORT="1883" \
  -e MQTT_TOPIC_PREFIX="printguard" \
  -e DEVICE_ID="printguard-mjpeg-1" \
  -e DEVICE_NAME="PrintGuard MJPEG" \
  printguard-headless:local
```

If your broker requires authentication, also set:

- `MQTT_USERNAME`
- `MQTT_PASSWORD`

## Environment Variables

Required:

- `MJPEG_URL`
- `MQTT_HOST`

Core optional settings:

- `MQTT_PORT` default `1883`
- `MQTT_TOPIC_PREFIX` default `printguard`
- `MQTT_CLIENT_ID` default `<device_id>-client`
- `MQTT_DISCOVERY_PREFIX` default `homeassistant`
- `MQTT_QOS` default `1`
- `MQTT_RETAIN_DISCOVERY` default `true`
- `MQTT_RETAIN_STATE` default `true`
- `MQTT_RETRY_DELAY_MS` default `5000`
- `DEVICE_ID` default `printguard-mjpeg-1`
- `DEVICE_NAME` default `PrintGuard MJPEG`
- `DETECTION_INTERVAL_MS` default `1000`
- `STREAM_OPEN_TIMEOUT_MS` default `5000`
- `STREAM_RETRY_DELAY_MS` default `5000`
- `ENABLED` default `true`
- `LOG_LEVEL` default `INFO`

Advanced model path overrides are available but normally not needed:

- `MODEL_PATH`
- `MODEL_OPTIONS_PATH`
- `PROTOTYPES_PATH`

## MQTT Topics

Base state topics use `MQTT_TOPIC_PREFIX`.

If `MQTT_TOPIC_PREFIX=printguard`, the service publishes:

- `printguard/availability`
- `printguard/status/state`
- `printguard/stream/state`
- `printguard/classification/state`
- `printguard/error/state`
- `printguard/last_inference_ts/state`
- `printguard/enabled/state`
- `printguard/enabled/set`

## Payload Semantics

- `availability`: `online` or `offline`
- `status/state`: `starting`, `online`, `offline`, or `disabled`
- `stream/state`: `ON` or `OFF`
- `classification/state`: `success`, `failure`, or `unknown`
- `error/state`: latest human-readable error string
- `last_inference_ts/state`: ISO 8601 UTC timestamp
- `enabled/state`: `ON` or `OFF`
- `enabled/set`: accepts `ON` or `OFF`

## Home Assistant Discovery

Discovery topics use `MQTT_DISCOVERY_PREFIX`.

If `MQTT_DISCOVERY_PREFIX=homeassistant` and `DEVICE_ID=printguard-mjpeg-1`, the service publishes retained discovery payloads for:

- `homeassistant/binary_sensor/printguard-mjpeg-1_stream/config`
- `homeassistant/sensor/printguard-mjpeg-1_classification/config`
- `homeassistant/sensor/printguard-mjpeg-1_status/config`
- `homeassistant/sensor/printguard-mjpeg-1_last_error/config`
- `homeassistant/sensor/printguard-mjpeg-1_last_inference_ts/config`
- `homeassistant/switch/printguard-mjpeg-1_enabled/config`

The entities are grouped under one Home Assistant device.

## Operational Notes

- stream open failure is reported as `status=offline` and `stream=OFF`
- repeated frame read failures also move the service to offline state
- the service retries forever after stream outages
- classification labels currently mirror the original model classes: `success` and `failure`
- this service reflects stream availability, not actual printer power state, unless your MJPEG stream only exists when the printer is on

## Current Limitations

- ONNX Runtime only
- one MJPEG stream only
- no HTTP API
- no historical storage
- no confidence score entity yet
- no explicit printer integration
