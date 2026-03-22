# PrintGuard

PrintGuard is a small headless service that:

- reads one MJPEG stream
- classifies frames with a baked-in ONNX model
- publishes Home Assistant compatible MQTT discovery and state topics
- retries automatically when the stream goes away

There is no web UI, REST API, database, or printer integration anymore.

## Main Files

- `Dockerfile` builds the service image and downloads the model at build time
- `docker-compose.yml` starts the service with a bundled Mosquitto broker
- `printguard/` contains the runtime code
- `scripts/download_model.py` downloads and normalizes the model artifacts for the image build
- `printguard-addon/` contains the Home Assistant add-on metadata

## Build

```bash
docker build -t printguard:local .
```

The model is baked into the image at build time under `/opt/printguard/model`.

## Releases

- versioning starts from `0.1.0` and stays in the `0.x` series until the service feels stable enough for `1.0.0`
- Release Please manages changelog updates, version bumps, release PRs, and GitHub releases
- use Conventional Commits for changes that should appear cleanly in releases, for example `feat:`, `fix:`, or `feat!:`
- pushes to `main` only run Release Please; the GHCR image is published only when a Release Please release is created

## Run

```bash
docker run --rm \
  -e MJPEG_URL="http://printer.local:8080/?action=stream" \
  -e MQTT_HOST="mqtt.local" \
  -e MQTT_PORT="1883" \
  -e MQTT_TOPIC_PREFIX="printguard" \
  -e DEVICE_ID="printguard-mjpeg-1" \
  -e DEVICE_NAME="PrintGuard MJPEG" \
  printguard:local
```

Required env vars:

- `MJPEG_URL`
- `MQTT_HOST`

Useful optional env vars:

- `MQTT_PORT` default `1883`
- `MQTT_TOPIC_PREFIX` default `printguard`
- `MQTT_DISCOVERY_PREFIX` default `homeassistant`
- `MQTT_USERNAME`
- `MQTT_PASSWORD`
- `DEVICE_ID` default `printguard-mjpeg-1`
- `DEVICE_NAME` default `PrintGuard MJPEG`
- `DETECTION_INTERVAL_MS` default `1000`
- `STREAM_OPEN_TIMEOUT_MS` default `5000`
- `STREAM_RETRY_DELAY_MS` default `5000`
- `MQTT_RETRY_DELAY_MS` default `5000`
- `LOG_LEVEL` default `INFO`; set `DEBUG` to log per-frame model outputs and outgoing MQTT publishes

## Compose

```bash
docker compose up --build -d
```

Before starting, update `MJPEG_URL` in `docker-compose.yml`.

## Home Assistant Add-on

This repo also acts as a custom Home Assistant add-on repository.

Install flow:

1. Open the Home Assistant Add-on Store
2. Add `https://github.com/Meightem/PrintGuard` as a custom repository
3. Install `PrintGuard`
4. Set `mjpeg_url` and `mqtt_host`
5. Start the add-on

The add-on metadata lives in `printguard-addon/config.yaml` and the runtime reads add-on options from `/data/options.json` automatically.

## MQTT Output

With `MQTT_TOPIC_PREFIX=printguard`, the service publishes:

- `printguard/availability`
- `printguard/status/state`
- `printguard/stream/state`
- `printguard/classification/state`
- `printguard/classification_confidence/state`
- `printguard/failure_confidence/state`
- `printguard/severity/state`
- `printguard/defect/state`
- `printguard/error/state`
- `printguard/last_inference_ts/state`

Home Assistant discovery topics are published under `homeassistant/` by default.

## Notes

- `stream/state=OFF` means the MJPEG stream could not be opened or frames stopped arriving
- `classification_confidence/state` is the derived confidence for the selected class in percent
- `failure_confidence/state` is the derived confidence that the frame looks like a failure in percent
- `severity/state` is `clear`, `warning`, `error`, or `unknown`; it is derived from failure confidence and is not a calibrated probability
- `defect/state=ON` means the current classification is `failure`
- `last_inference_ts/state` is `unknown` until the first successful inference
- `LOG_LEVEL=DEBUG` enables verbose logs from `printguard.prediction` and `printguard.mqtt.publish`, including the exact MQTT topics and payloads being sent
- the service is always enabled; there is no MQTT or Home Assistant toggle anymore
- the service reports stream availability, not actual printer power state, unless your stream only exists while the printer is on
