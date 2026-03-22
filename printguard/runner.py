import logging
import time
from datetime import datetime, timezone

import cv2

from .config import Settings
from .home_assistant import build_topics, publish_discovery
from .model import ONNXClassifier
from .mqtt import MQTTClient


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
        cap = cv2.VideoCapture(self.settings.mjpeg_url, cv2.CAP_ANY)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, self.settings.stream_open_timeout_ms)
        if not cap.isOpened():
            self._publish_stream_error("Failed to open MJPEG stream")
            time.sleep(self.settings.stream_retry_delay_ms / 1000.0)
            return
        LOGGER.info("Connected to MJPEG stream")
        self._publish_stream_online()
        last_inference_at = 0.0
        consecutive_failures = 0
        try:
            while self.enabled:
                ok, frame = cap.read()
                if not ok or frame is None:
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
                label = self.classifier.classify_frame(frame)
                last_inference_at = now
                self._publish_classification(label)
        except Exception as exc:
            LOGGER.exception("Unhandled stream session error")
            self._publish_stream_error(str(exc))
        finally:
            cap.release()
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
        self.defect_state = "OFF"
        self._publish_current_state()

    def _publish_stream_online(self) -> None:
        self.current_status = "online"
        self.stream_state = "ON"
        self.last_error = ""
        self._publish_current_state()

    def _publish_stream_error(self, error_message: str) -> None:
        LOGGER.warning("Stream error: %s", error_message)
        self.current_status = "offline"
        self.stream_state = "OFF"
        self.defect_state = "OFF"
        self.last_error = error_message
        self._publish_current_state()

    def _publish_classification(self, label: str) -> None:
        self.last_classification = label
        self.defect_state = "ON" if label == "failure" else "OFF"
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
