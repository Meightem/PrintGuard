# PrintGuard Headless MQTT Service Plan

## Goal

Refactor this repository from a web-based multi-camera monitoring application into a small, single-purpose service that:

- reads one MJPEG stream URL from configuration
- classifies frames with the existing PrintGuard model
- publishes status and classification results to MQTT
- integrates cleanly with Home Assistant via MQTT Discovery
- runs as a single Docker container with the model baked into the image

This document is the working plan for that simplification effort.

## Target Behavior

The final service should:

- start from static configuration only
- expose no HTTP API, web UI, SSE, or interactive setup flow
- maintain no persistent application state beyond in-memory runtime status
- connect to one MJPEG stream source
- continuously evaluate frames with the ONNX model
- publish Home Assistant-compatible MQTT entities and state updates
- reconnect automatically when the stream becomes unavailable
- treat stream unavailability as an offline condition in MQTT output

## Non-Goals

The simplified service should not include:

- FastAPI routes
- web UI
- SSE streaming
- web push notifications
- multi-camera support
- printer service integrations such as OctoPrint
- dynamic runtime configuration through endpoints
- runtime model downloads
- PyTorch runtime support

## Runtime Model Strategy

The runtime service should assume model files already exist at fixed paths inside the container.

Recommended runtime paths:

- `/opt/printguard/model/model.onnx`
- `/opt/printguard/model/opt.json`
- `/opt/printguard/model/prototypes/cache/prototypes.pkl`

Requirements:

- model downloads happen only during image build
- Python runtime code does not call Hugging Face or any downloader automatically
- a standalone maintenance script may still exist to download or refresh model artifacts manually
- runtime startup should fail clearly if required model files are missing

## Inference Runtime Direction

The simplified service should standardize on ONNX Runtime only.

Implications:

- remove backend auto-detection from the service path
- remove PyTorch as a runtime dependency for the deployed image
- always load the ONNX model from the fixed baked-in path
- keep only the inference code needed to preprocess frames, load prototypes, and classify images

## Input Model

Configuration should be static and environment-driven.

Minimum required configuration:

- `MJPEG_URL`
- `MQTT_HOST`
- `MQTT_PORT`
- `MQTT_TOPIC_PREFIX`

Recommended optional configuration:

- `MQTT_USERNAME`
- `MQTT_PASSWORD`
- `MQTT_CLIENT_ID`
- `MQTT_DISCOVERY_PREFIX` default `homeassistant`
- `MQTT_QOS`
- `MQTT_RETAIN_DISCOVERY` default `true`
- `MQTT_RETAIN_STATE` default `true`
- `DEVICE_NAME`
- `DEVICE_ID`
- `DETECTION_INTERVAL_MS`
- `STREAM_OPEN_TIMEOUT_MS`
- `STREAM_RETRY_DELAY_MS`
- `LOG_LEVEL`
- `ENABLED` default `true`

## Output Model

The service should publish a small set of MQTT topics for Home Assistant.

### Device Identity

All Home Assistant entities should share one MQTT Discovery `device` block, for example:

```json
{
  "identifiers": ["printguard-mjpeg-1"],
  "name": "PrintGuard MJPEG",
  "manufacturer": "PrintGuard",
  "model": "Headless MJPEG Monitor",
  "sw_version": "planned"
}
```

### Availability Topic

Base availability topic:

- `<topic_prefix>/availability`

Payloads:

- `online`
- `offline`

### Core State Topics

Recommended state topics:

- `<topic_prefix>/status/state`
- `<topic_prefix>/stream/state`
- `<topic_prefix>/classification/state`
- `<topic_prefix>/error/state`
- `<topic_prefix>/last_inference_ts/state`
- `<topic_prefix>/enabled/state`

Optional command topic:

- `<topic_prefix>/enabled/set`

### Semantic Meanings

- `status/state`: service lifecycle state such as `starting`, `online`, `offline`, `error`, `disabled`
- `stream/state`: stream availability such as `ON` or `OFF`
- `classification/state`: latest model output such as `success`, `failure`, or `unknown`
- `error/state`: latest human-readable error string
- `last_inference_ts/state`: timestamp of latest successful inference
- `enabled/state`: whether inference is enabled

## Home Assistant Discovery Plan

The service should publish retained MQTT Discovery payloads at startup.

Recommended entities:

1. `binary_sensor` for stream availability
2. `sensor` for classification result
3. `sensor` for service status
4. `sensor` for last error
5. `sensor` for last inference timestamp
6. optional `switch` for enabling or disabling inference

Recommended discovery topics:

- `<discovery_prefix>/binary_sensor/<device_id>_stream/config`
- `<discovery_prefix>/sensor/<device_id>_classification/config`
- `<discovery_prefix>/sensor/<device_id>_status/config`
- `<discovery_prefix>/sensor/<device_id>_last_error/config`
- `<discovery_prefix>/sensor/<device_id>_last_inference_ts/config`
- `<discovery_prefix>/switch/<device_id>_enabled/config` optional

Each discovery payload should include at least:

- `unique_id`
- `name`
- `state_topic`
- `availability_topic`
- `payload_available`
- `payload_not_available`
- `device`

## Error Handling Expectations

The service should be resilient and self-healing.

Expected behavior:

- if the stream cannot be opened, publish offline status and retry
- if frame reads fail repeatedly, publish offline status and retry reconnecting
- if MQTT disconnects, reconnect automatically and restore discovery/state
- if inference fails for a frame, publish an error state but keep the process alive where possible
- if model files are missing at startup, fail fast with a clear log message

Important semantic note:

This service can reliably observe stream availability, not true printer electrical power state.
If the MJPEG stream only exists while the printer is on, then stream availability can be treated operationally as printer availability. Otherwise the published state should be understood as stream status.

## Proposed Runtime Loop

High-level loop:

1. load static configuration
2. connect to MQTT broker
3. publish Home Assistant discovery payloads
4. publish initial availability and startup state
5. load ONNX model and prototypes from fixed local paths
6. open MJPEG stream
7. if stream is available, read frames and run inference at configured interval
8. publish classification and status updates to MQTT
9. if stream fails, publish offline state and retry until recovered
10. repeat forever

## Proposed Project Restructure

The current repository contains much more functionality than needed. The target architecture should be a small headless worker.

Recommended new modules:

- `service/config.py`
- `service/model.py`
- `service/stream.py`
- `service/mqtt.py`
- `service/home_assistant.py`
- `service/runner.py`
- `service/main.py`

Likely reusable code sources from the current repository:

- ONNX inference support from `printguard/utils/backends/onnxruntime_engine.py`
- shared model utility patterns from `printguard/utils/model_utils.py`
- parts of the current frame processing loop from `printguard/utils/stream_utils.py`
- model artifact download logic pattern from `printguard/utils/model_downloader.py`

Likely removable application areas:

- `printguard/routes/`
- `printguard/utils/sse_utils.py`
- `printguard/utils/notification_utils.py`
- printer integration code
- setup and tunnel-related code

## Docker Strategy

The Docker image should be the primary deployment artifact.

Recommended approach:

- use a build stage that installs the minimal tooling needed to download model assets
- run a dedicated model download script during image build
- copy the model artifacts into the final runtime image
- install only runtime dependencies required for ONNX inference, OpenCV, MQTT, and configuration
- set the container entrypoint to the headless worker

Docker expectations:

- no runtime model fetching
- deterministic image contents
- simple env-based configuration
- suitable for use with Docker Compose or direct `docker run`

## Planned Simplifications

These are the intended implementation choices unless later requirements change:

- single MJPEG input only
- ONNX Runtime only
- MQTT as the only integration surface
- Home Assistant discovery enabled by default
- no persisted config database or keyring
- no REST endpoints
- no multi-user or browser workflow
- no printer API control

## Open Questions To Confirm During Implementation

These details are still worth validating while coding:

- whether OpenCV alone is reliable enough for the specific MJPEG stream source in production
- whether Home Assistant should receive the latest state as retained messages for all entities or only selected ones
- whether the optional HA `switch.enabled` actuator should be implemented in the first version
- whether a JSON attributes topic is useful for extra debugging metadata such as backend, retry count, and frame timestamps
- whether the classification output should stay as the raw labels `success` and `failure` or be translated to more user-friendly strings

## Initial Implementation Checklist

1. create the new headless service module layout
2. add a build-time model download script
3. lock runtime inference to ONNX only
4. implement MQTT client and reconnection behavior
5. implement Home Assistant discovery publishing
6. implement MJPEG read and reconnect loop
7. implement frame classification publishing
8. remove or isolate web app code from the deployment path
9. create a minimal Dockerfile for the headless service
10. document configuration, topics, and example deployment

## Success Criteria

This plan is complete when the project can be built into one Docker image that:

- contains the ONNX model already baked in
- starts without any HTTP server
- reads one MJPEG stream URL from configuration
- publishes Home Assistant-discoverable MQTT entities automatically
- reports stream availability and inference results continuously
- survives stream outages and reconnects automatically
