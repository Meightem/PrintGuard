import json
import logging
import threading
import time
from typing import Callable

import paho.mqtt.client as mqtt


LOGGER = logging.getLogger(__name__)


class MQTTClient:
    def __init__(
        self,
        host: str,
        port: int,
        client_id: str,
        username: str,
        password: str,
        qos: int,
        retry_delay_ms: int,
    ):
        self.host = host
        self.port = port
        self.qos = qos
        self.retry_delay_ms = retry_delay_ms
        self._connected = threading.Event()
        self._command_handlers: dict[str, Callable[[str], None]] = {}
        self._connect_handlers: list[Callable[[], None]] = []
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        if username:
            self._client.username_pw_set(username, password=password or None)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)

    def connect(self, availability_topic: str) -> None:
        self._client.will_set(availability_topic, payload="offline", qos=self.qos, retain=True)
        self._client.loop_start()
        while True:
            try:
                self._client.connect(self.host, self.port, keepalive=60)
                return
            except Exception as exc:
                LOGGER.warning(
                    "Initial MQTT connect failed: %s. Retrying in %.1fs",
                    exc,
                    self.retry_delay_ms / 1000.0,
                )
                time.sleep(self.retry_delay_ms / 1000.0)

    def disconnect(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()

    def wait_until_connected(self, timeout: float = 30.0) -> bool:
        return self._connected.wait(timeout=timeout)

    def publish(self, topic: str, payload: str | dict, retain: bool = True) -> None:
        if isinstance(payload, dict):
            payload = json.dumps(payload, separators=(",", ":"))
        self._client.publish(topic, payload=payload, qos=self.qos, retain=retain)

    def subscribe(self, topic: str, handler: Callable[[str], None]) -> None:
        self._command_handlers[topic] = handler
        if self._connected.is_set():
            self._client.subscribe(topic, qos=self.qos)

    def add_connect_handler(self, handler: Callable[[], None]) -> None:
        self._connect_handlers.append(handler)

    def _on_connect(self, client: mqtt.Client, _userdata, _flags, reason_code, _properties) -> None:
        if reason_code.is_failure:
            LOGGER.error("MQTT connection failed: %s", reason_code)
            return
        LOGGER.info("Connected to MQTT broker at %s:%s", self.host, self.port)
        self._connected.set()
        for topic in self._command_handlers:
            client.subscribe(topic, qos=self.qos)
        for handler in self._connect_handlers:
            handler()

    def _on_disconnect(self, _client: mqtt.Client, _userdata, _flags, reason_code, _properties) -> None:
        self._connected.clear()
        if reason_code != 0:
            LOGGER.warning("Disconnected from MQTT broker: %s", reason_code)

    def _on_message(self, _client: mqtt.Client, _userdata, msg: mqtt.MQTTMessage) -> None:
        handler = self._command_handlers.get(msg.topic)
        if handler is None:
            return
        payload = msg.payload.decode("utf-8", errors="replace")
        handler(payload)
