# PrintGuard for Home Assistant

[![Release](https://img.shields.io/github/v/release/Meightem/PrintGuard?sort=semver)](https://github.com/Meightem/PrintGuard/releases)
[![License](https://img.shields.io/github/license/Meightem/PrintGuard)](LICENSE.md)

PrintGuard is a small Home Assistant add-on that watches one MJPEG camera feed, runs the original PrintGuard defect model, and publishes the results over MQTT with Home Assistant auto-discovery.

In other words: point a printer webcam at your print, let the model stare at it, and let Home Assistant do the dashboard part.

> This fork is heavily adapted from the original PrintGuard project by Oliver Bravery. This version is intentionally stripped down, Home Assistant-focused, and yes, very much vibe-coded.

## What It Is

- one MJPEG webcam stream in
- one ONNX model baked into the container image
- MQTT discovery sensors out
- no web UI
- no REST API
- no printer control
- no database

This repo is first and foremost a custom Home Assistant add-on repository.

## How It Works

1. Home Assistant runs the add-on
2. the add-on connects to your MJPEG stream
3. each frame is classified with the PrintGuard model
4. the add-on publishes MQTT topics and Home Assistant discovery payloads
5. Home Assistant creates the entities automatically

No HACS integration is required. MQTT discovery does the heavy lifting.

## Home Assistant Install

1. Open `Settings -> Add-ons -> Add-on Store`
2. Open the menu in the top right and choose `Repositories`
3. Add this repository:
   - `https://github.com/Meightem/PrintGuard`
4. Install `PrintGuard`
5. Set at least:
   - `mjpeg_url`
   - `mqtt_host`
6. Start the add-on

If you use the official Mosquitto add-on, `mqtt_host: core-mosquitto` is usually the right choice.

## What Home Assistant Gets

With `mqtt_topic_prefix=printguard`, the add-on publishes these core topics:

| Topic | Meaning |
| --- | --- |
| `printguard/availability` | add-on availability |
| `printguard/status/state` | overall service state |
| `printguard/stream/state` | MJPEG stream status |
| `printguard/classification/state` | confirmed `success` or `failure` |
| `printguard/print_quality/state` | derived print quality score from `1` to `10` |

Home Assistant discovery topics are published under `homeassistant/` by default.

The discovered entities are intentionally minimal:

- `Classification`
- `Status`
- `Stream`
- `Print Quality`

## Print Quality Scale

`Print Quality` is a derived score from `1` to `10`.

| Score | Meaning |
| --- | --- |
| `1` | There is a print failure |
| `2` | There is probably a print failure |
| `3` | There might be a print failure |
| `4` | Monitoring a possible print issue |
| `5` | Monitoring a possible print issue |
| `6` | Good print quality |
| `7` | Good print quality |
| `8` | Great print quality |
| `9` | Great print quality |
| `10` | Perfect print quality |

Important caveat:

- this repo does not currently include a separate temporal combination model
- the current score is derived from a temporally smoothed failure-confidence signal
- it is useful as a UI/status value, not as a hard safety signal

## Current Behavior

- `Classification` is not a raw single-frame label; it uses the original-style majority vote confirmation and only flips to `failure` after repeated recent failure predictions
- stable good-state MQTT updates are rate-limited; important changes still publish quickly
- `Stream=OFF` means the MJPEG stream could not be opened or stopped delivering frames
- the add-on reports stream availability, not actual printer power state, unless your stream only exists while the printer is on

## Configuration

Required add-on options:

- `mjpeg_url`
- `mqtt_host`

Useful optional options:

- `mqtt_port`
- `mqtt_topic_prefix`
- `mqtt_discovery_prefix`
- `mqtt_username`
- `mqtt_password`
- `device_id`
- `device_name`
- `detection_interval_ms`
- `stream_open_timeout_ms`
- `stream_retry_delay_ms`
- `mqtt_retry_delay_ms`
- `log_level`

Set `log_level: DEBUG` if you want detailed model logs and exact outgoing MQTT payload logs.

## Upstream and Attribution

This project is heavily derived from the original PrintGuard project:

- upstream repo: `https://github.com/oliverbravery/PrintGuard`
- original author: Oliver Bravery

The original project was a broader print monitoring application with a web UI and more runtime components. This fork trims that down to a single job: Home Assistant add-on, webcam in, MQTT out.

The model, general inference flow, and overall project direction all come from that upstream work. This fork mainly repackages and simplifies it for a different deployment style.

## Development

<details>
<summary>Local development notes</summary>

Build the image:

```bash
docker build -t printguard:local .
```

Run with Docker:

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

Run the bundled local stack:

```bash
docker compose up --build -d
```

This repo uses Release Please for releases. New container images are published from GitHub releases, not from every push.

</details>

## License

This repository remains under GPL-2.0 terms, following the upstream project. See `LICENSE.md`.
