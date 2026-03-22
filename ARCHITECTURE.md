# Architecture

## Runtime Flow

1. `printguard.main` loads and validates configuration, configures logging, and wires signal handling.
2. `printguard.runner.HeadlessService` orchestrates model loading, MQTT connectivity, stream sessions, and shutdown.
3. `printguard.stream` provides frame sources for HTTP MJPEG or OpenCV-backed transports.
4. `printguard.model` loads ONNX artifacts and produces per-frame predictions.
5. `printguard.policy` converts raw predictions into stable user-facing classification and print-quality values.
6. `printguard.state` throttles MQTT state publication and heartbeat behavior.
7. `printguard.health` writes a local health snapshot that powers the container `HEALTHCHECK`.

## Design Principles

- keep transport, policy, and publication concerns separate
- keep runtime state explicit through typed snapshots and enums
- fail fast on invalid configuration
- prefer simple files and local health signals over adding a web control plane
