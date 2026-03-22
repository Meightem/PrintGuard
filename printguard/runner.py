import logging
import time
from dataclasses import replace

from .config import Settings
from .domain import (
    ClassificationState,
    ServiceSnapshot,
    ServiceStatus,
    StreamState,
)
from .health import HealthStateStore
from .home_assistant import build_topics, publish_discovery
from .model import ONNXClassifier, PredictionResult
from .mqtt import MQTTClient
from .policy import ClassificationPolicy
from .state import MQTTStatePublisher
from .stream import create_frame_source

LOGGER = logging.getLogger(__name__)


class HeadlessService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.topics = build_topics(settings)
        self.mqtt = MQTTClient(
            host=settings.mqtt_host,
            port=settings.mqtt_port,
            client_id=settings.mqtt_client_id,
            username=settings.mqtt_username,
            password=settings.mqtt_password,
            qos=settings.mqtt_qos,
            retry_delay_ms=settings.mqtt_retry_delay_ms,
            connect_timeout_seconds=settings.mqtt_connect_timeout_seconds,
            connect_max_attempts=settings.mqtt_connect_max_attempts,
            tls_enabled=settings.mqtt_tls_enabled,
            tls_insecure=settings.mqtt_tls_insecure,
            tls_ca_path=settings.mqtt_tls_ca_path,
            tls_certfile=settings.mqtt_tls_certfile,
            tls_keyfile=settings.mqtt_tls_keyfile,
        )
        self.classifier = ONNXClassifier(
            model_path=settings.model_path,
            options_path=settings.model_options_path,
            prototypes_path=settings.prototypes_path,
        )
        self.snapshot = ServiceSnapshot()
        self.classification_policy = ClassificationPolicy()
        self.state_publisher = MQTTStatePublisher(
            self.mqtt,
            self.topics,
            retain_state=settings.mqtt_retain_state,
        )
        self.health = HealthStateStore(settings.health_path)
        self.health.update(self.snapshot, error="service starting")
        self.mqtt.add_connect_handler(self._publish_discovery_state)

    def run(self) -> None:
        self.classifier.load()
        self.mqtt.connect(self.topics.availability)
        if not self.mqtt.wait_until_connected():
            raise RuntimeError("Failed to connect to MQTT broker within timeout")
        while True:
            self._run_stream_session()

    def stop(self) -> None:
        stopped_snapshot = replace(
            self.snapshot,
            status=ServiceStatus.OFFLINE,
            stream=StreamState.OFF,
            classification=ClassificationState.UNKNOWN,
            print_quality="unknown",
        )
        self.snapshot = stopped_snapshot
        self.health.update(stopped_snapshot, error="service stopped")
        try:
            self.mqtt.publish(self.topics.availability, "offline", retain=True)
        finally:
            self.mqtt.disconnect()

    def _publish_discovery_state(self) -> None:
        publish_discovery(self.mqtt, self.settings, self.topics)
        self.mqtt.publish(self.topics.availability, "online", retain=True)
        self._publish_snapshot(force=True)

    def _run_stream_session(self) -> None:
        frame_source = create_frame_source(
            self.settings.mjpeg_url,
            self.settings.stream_open_timeout_ms,
        )
        try:
            frame_source.open()
        except Exception as exc:
            self._publish_stream_error(str(exc) or "Failed to open MJPEG stream")
            time.sleep(self.settings.stream_retry_delay_ms / 1000.0)
            return
        LOGGER.info("Connected to MJPEG stream")
        self._publish_stream_online()
        last_inference_at = 0.0
        consecutive_failures = 0
        try:
            while True:
                frame = frame_source.read_frame()
                if frame is None:
                    consecutive_failures += 1
                    if consecutive_failures >= self.settings.stream_read_failure_limit:
                        self._publish_stream_error("MJPEG stream read failed")
                        return
                    time.sleep(0.2)
                    continue
                consecutive_failures = 0
                now = time.time()
                if now - last_inference_at < (
                    self.settings.detection_interval_ms / 1000.0
                ):
                    continue
                prediction = self.classifier.classify_frame(frame)
                last_inference_at = now
                self._publish_classification(prediction, inference_at=now)
        except Exception as exc:
            LOGGER.exception("Unhandled stream session error")
            self._publish_stream_error(str(exc))
        finally:
            frame_source.close()
            time.sleep(self.settings.stream_retry_delay_ms / 1000.0)

    def _publish_snapshot(
        self,
        *,
        force: bool = False,
        error: str | None = None,
        inference_at: float | None = None,
    ) -> None:
        now_monotonic = time.monotonic()
        self.state_publisher.publish(
            self.snapshot,
            now_monotonic=now_monotonic,
            force=force,
        )
        self.health.update(self.snapshot, error=error, inference_at=inference_at)

    def _publish_stream_online(self) -> None:
        self.classification_policy.reset()
        self.snapshot = ServiceSnapshot(
            status=ServiceStatus.ONLINE,
            stream=StreamState.ON,
            classification=ClassificationState.UNKNOWN,
            print_quality="unknown",
        )
        self._publish_snapshot(force=True)

    def _publish_stream_error(self, error_message: str) -> None:
        LOGGER.warning("Stream error: %s", error_message)
        self.classification_policy.reset()
        self.snapshot = ServiceSnapshot(
            status=ServiceStatus.OFFLINE,
            stream=StreamState.OFF,
            classification=ClassificationState.UNKNOWN,
            print_quality="unknown",
        )
        self._publish_snapshot(force=True, error=error_message)

    def _publish_classification(
        self,
        prediction: PredictionResult,
        *,
        inference_at: float,
    ) -> None:
        outcome = self.classification_policy.observe(prediction)
        self.snapshot = ServiceSnapshot(
            status=ServiceStatus.ONLINE,
            stream=StreamState.ON,
            classification=outcome.classification,
            print_quality=outcome.print_quality,
        )
        self._publish_snapshot(inference_at=inference_at)
