import logging
import time
from collections import deque

from .config import Settings
from .home_assistant import build_topics, publish_discovery
from .model import ONNXClassifier, PredictionResult
from .mqtt import MQTTClient
from .stream import create_frame_source


LOGGER = logging.getLogger(__name__)
QUALITY_SMOOTHING_ALPHA = 0.35
STATE_HEARTBEAT_SECONDS = 60.0
RAPID_QUALITY_DROP = 2
WATCH_QUALITY_THRESHOLD = 5
DEFECT_VOTING_WINDOW = 5
DEFECT_VOTING_THRESHOLD = 2


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
        )
        self.classifier = ONNXClassifier(
            model_path=settings.model_path,
            options_path=settings.model_options_path,
            prototypes_path=settings.prototypes_path,
        )
        self.current_status = "starting"
        self.stream_state = "OFF"
        self.last_classification = "unknown"
        self.last_print_quality = "unknown"
        self.smoothed_failure_confidence: float | None = None
        self._recent_raw_labels: deque[str] = deque(maxlen=DEFECT_VOTING_WINDOW)
        self._last_published_state: dict[str, str] = {}
        self._last_publish_monotonic = 0.0
        self.mqtt.add_connect_handler(self._publish_discovery_state)

    def run(self) -> None:
        self.classifier.load()
        self.mqtt.connect(self.topics.availability)
        if not self.mqtt.wait_until_connected():
            raise RuntimeError("Failed to connect to MQTT broker within timeout")
        while True:
            self._run_stream_session()

    def stop(self) -> None:
        try:
            self.mqtt.publish(self.topics.availability, "offline", retain=True)
        finally:
            self.mqtt.disconnect()

    def _publish_discovery_state(self) -> None:
        publish_discovery(self.mqtt, self.settings, self.topics)
        self.mqtt.publish(self.topics.availability, "online", retain=True)
        self._publish_current_state(force=True)

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
                    if consecutive_failures >= 5:
                        self._publish_stream_error("MJPEG stream read failed")
                        return
                    time.sleep(0.2)
                    continue
                consecutive_failures = 0
                now = time.time()
                if now - last_inference_at < (self.settings.detection_interval_ms / 1000.0):
                    continue
                prediction = self.classifier.classify_frame(frame)
                last_inference_at = now
                self._publish_classification(prediction)
        except Exception as exc:
            LOGGER.exception("Unhandled stream session error")
            self._publish_stream_error(str(exc))
        finally:
            frame_source.close()
            time.sleep(self.settings.stream_retry_delay_ms / 1000.0)

    def _publish_current_state(self, force: bool = False) -> None:
        snapshot = self._current_snapshot()
        now = time.monotonic()
        changed_keys = [
            key
            for key, value in snapshot.items()
            if self._last_published_state.get(key) != value
        ]
        if not force and not changed_keys and now - self._last_publish_monotonic < STATE_HEARTBEAT_SECONDS:
            return
        if not force and not self._should_publish_now(snapshot, changed_keys, now):
            return
        publish_keys = list(snapshot) if force or now - self._last_publish_monotonic >= STATE_HEARTBEAT_SECONDS else changed_keys
        for key in publish_keys:
            self.mqtt.publish(
                key,
                snapshot[key],
                retain=self.settings.mqtt_retain_state,
            )
        self._last_published_state = snapshot
        self._last_publish_monotonic = now

    def _publish_stream_online(self) -> None:
        self.current_status = "online"
        self.stream_state = "ON"
        self.last_classification = "unknown"
        self.last_print_quality = "unknown"
        self.smoothed_failure_confidence = None
        self._recent_raw_labels.clear()
        self._publish_current_state(force=True)

    def _publish_stream_error(self, error_message: str) -> None:
        LOGGER.warning("Stream error: %s", error_message)
        self.current_status = "offline"
        self.stream_state = "OFF"
        self.last_classification = "unknown"
        self.last_print_quality = "unknown"
        self.smoothed_failure_confidence = None
        self._recent_raw_labels.clear()
        self._publish_current_state(force=True)

    def _publish_classification(self, prediction: PredictionResult) -> None:
        self._recent_raw_labels.append(prediction.label)
        self.last_classification = self._confirm_classification(prediction.label)
        self.smoothed_failure_confidence = self._smooth_failure_confidence(
            prediction.failure_confidence
        )
        self.last_print_quality = str(
            self._failure_confidence_to_quality(self.smoothed_failure_confidence)
        )
        self.current_status = "online"
        self.stream_state = "ON"
        self._publish_current_state()

    def _current_snapshot(self) -> dict[str, str]:
        return {
            self.topics.status_state: self.current_status,
            self.topics.stream_state: self.stream_state,
            self.topics.classification_state: self.last_classification,
            self.topics.print_quality_state: self.last_print_quality,
        }

    def _should_publish_now(
        self,
        snapshot: dict[str, str],
        changed_keys: list[str],
        now: float,
    ) -> bool:
        if now - self._last_publish_monotonic >= STATE_HEARTBEAT_SECONDS:
            return True
        immediate_keys = {
            self.topics.status_state,
            self.topics.stream_state,
            self.topics.classification_state,
        }
        if any(key in immediate_keys for key in changed_keys):
            return True
        previous_quality = self._parse_quality(self._last_published_state.get(self.topics.print_quality_state))
        current_quality = self._parse_quality(snapshot[self.topics.print_quality_state])
        if previous_quality is None or current_quality is None:
            return False
        if current_quality <= WATCH_QUALITY_THRESHOLD and current_quality != previous_quality:
            return True
        return previous_quality - current_quality >= RAPID_QUALITY_DROP

    @staticmethod
    def _failure_confidence_to_quality(failure_confidence: float) -> int:
        thresholds = [0.95, 0.85, 0.75, 0.65, 0.55, 0.45, 0.35, 0.25, 0.15]
        for index, threshold in enumerate(thresholds, start=1):
            if failure_confidence >= threshold:
                return index
        return 10

    def _smooth_failure_confidence(self, failure_confidence: float) -> float:
        if self.smoothed_failure_confidence is None:
            return failure_confidence
        return (
            QUALITY_SMOOTHING_ALPHA * failure_confidence
            + (1.0 - QUALITY_SMOOTHING_ALPHA) * self.smoothed_failure_confidence
        )

    def _confirm_classification(self, raw_label: str) -> str:
        if raw_label != "failure":
            return "success"
        failure_votes = sum(1 for label in self._recent_raw_labels if label == "failure")
        if failure_votes >= DEFECT_VOTING_THRESHOLD:
            return "failure"
        return "success"

    @staticmethod
    def _parse_quality(value: str | None) -> int | None:
        if value is None or value == "unknown":
            return None
        return int(value)
