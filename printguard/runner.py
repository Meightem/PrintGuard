import logging
import time
from datetime import datetime, timezone

from .config import Settings
from .home_assistant import build_topics, publish_discovery
from .model import ONNXClassifier, PredictionResult
from .mqtt import MQTTClient
from .stream import create_frame_source


LOGGER = logging.getLogger(__name__)
WARNING_FAILURE_CONFIDENCE = 50.0
ERROR_FAILURE_CONFIDENCE = 75.0


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
        self.enabled = settings.enabled
        self.current_status = "starting"
        self.stream_state = "OFF"
        self.last_classification = "unknown"
        self.last_classification_confidence = "unknown"
        self.last_failure_confidence = "unknown"
        self.last_severity = "unknown"
        self.defect_state = "OFF"
        self.last_error = ""
        self.last_inference_ts = "unknown"
        self.mqtt.add_connect_handler(self._publish_discovery_state)

    def run(self) -> None:
        self.classifier.load()
        self.mqtt.connect(self.topics.availability)
        if not self.mqtt.wait_until_connected():
            raise RuntimeError("Failed to connect to MQTT broker within timeout")
        self.mqtt.subscribe(self.topics.enabled_set, self._handle_enabled_command)
        while True:
            if not self.enabled:
                self._publish_disabled_state()
                time.sleep(1.0)
                continue
            self._run_stream_session()

    def stop(self) -> None:
        try:
            self.mqtt.publish(self.topics.availability, "offline", retain=True)
        finally:
            self.mqtt.disconnect()

    def _publish_discovery_state(self) -> None:
        publish_discovery(self.mqtt, self.settings, self.topics)
        self._publish_current_state()

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
            while self.enabled:
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

    def _publish_current_state(self) -> None:
        self.mqtt.publish(self.topics.availability, "online", retain=True)
        self.mqtt.publish(
            self.topics.status_state,
            self.current_status,
            retain=self.settings.mqtt_retain_state,
        )
        self.mqtt.publish(self.topics.enabled_state, "ON" if self.enabled else "OFF", retain=True)
        self.mqtt.publish(self.topics.stream_state, self.stream_state, retain=True)
        self.mqtt.publish(
            self.topics.classification_state,
            self.last_classification,
            retain=self.settings.mqtt_retain_state,
        )
        self.mqtt.publish(
            self.topics.classification_confidence_state,
            self.last_classification_confidence,
            retain=self.settings.mqtt_retain_state,
        )
        self.mqtt.publish(
            self.topics.failure_confidence_state,
            self.last_failure_confidence,
            retain=self.settings.mqtt_retain_state,
        )
        self.mqtt.publish(
            self.topics.severity_state,
            self.last_severity,
            retain=self.settings.mqtt_retain_state,
        )
        self.mqtt.publish(self.topics.defect_state, self.defect_state, retain=True)
        self.mqtt.publish(self.topics.error_state, self.last_error, retain=True)
        self.mqtt.publish(
            self.topics.last_inference_ts_state,
            self.last_inference_ts,
            retain=self.settings.mqtt_retain_state,
        )

    def _publish_disabled_state(self) -> None:
        self.current_status = "disabled"
        self.stream_state = "OFF"
        self.last_classification = "unknown"
        self.last_classification_confidence = "unknown"
        self.last_failure_confidence = "unknown"
        self.last_severity = "unknown"
        self.defect_state = "OFF"
        self._publish_current_state()

    def _publish_stream_online(self) -> None:
        self.current_status = "online"
        self.stream_state = "ON"
        self.last_classification = "unknown"
        self.last_classification_confidence = "unknown"
        self.last_failure_confidence = "unknown"
        self.last_severity = "unknown"
        self.defect_state = "OFF"
        self.last_error = ""
        self._publish_current_state()

    def _publish_stream_error(self, error_message: str) -> None:
        LOGGER.warning("Stream error: %s", error_message)
        self.current_status = "offline"
        self.stream_state = "OFF"
        self.last_classification = "unknown"
        self.last_classification_confidence = "unknown"
        self.last_failure_confidence = "unknown"
        self.last_severity = "unknown"
        self.defect_state = "OFF"
        self.last_error = error_message
        self._publish_current_state()

    def _publish_classification(self, prediction: PredictionResult) -> None:
        self.last_classification = prediction.label
        self.last_classification_confidence = self._format_percentage(
            prediction.classification_confidence
        )
        self.last_failure_confidence = self._format_percentage(prediction.failure_confidence)
        self.last_severity = self._classify_severity(prediction.failure_confidence)
        self.defect_state = "ON" if prediction.label == "failure" else "OFF"
        self.last_inference_ts = datetime.now(timezone.utc).isoformat()
        self.current_status = "online"
        self.stream_state = "ON"
        self.last_error = ""
        self._publish_current_state()

    def _handle_enabled_command(self, payload: str) -> None:
        normalized = payload.strip().upper()
        if normalized == "ON":
            self.enabled = True
            self.current_status = "starting"
            self._publish_current_state()
        elif normalized == "OFF":
            self.enabled = False
            self.current_status = "disabled"
            self.stream_state = "OFF"
            self._publish_current_state()

    @staticmethod
    def _format_percentage(value: float) -> str:
        return f"{value * 100:.1f}"

    @staticmethod
    def _classify_severity(failure_confidence: float) -> str:
        failure_percentage = failure_confidence * 100.0
        if failure_percentage >= ERROR_FAILURE_CONFIDENCE:
            return "error"
        if failure_percentage >= WARNING_FAILURE_CONFIDENCE:
            return "warning"
        return "clear"
