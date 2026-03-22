from typing import Protocol

from .domain import ServiceSnapshot
from .home_assistant import DiscoveryTopics


class SupportsPublish(Protocol):
    def publish(self, topic: str, payload: str, retain: bool = True) -> None:
        ...


class MQTTStatePublisher:
    def __init__(
        self,
        mqtt: SupportsPublish,
        topics: DiscoveryTopics,
        *,
        retain_state: bool,
        heartbeat_seconds: float = 60.0,
        watch_quality_threshold: int = 5,
        rapid_quality_drop: int = 2,
    ) -> None:
        self.mqtt = mqtt
        self.topics = topics
        self.retain_state = retain_state
        self.heartbeat_seconds = heartbeat_seconds
        self.watch_quality_threshold = watch_quality_threshold
        self.rapid_quality_drop = rapid_quality_drop
        self.last_published_state: dict[str, str] = {}
        self.last_publish_monotonic = 0.0

    def publish(
        self,
        snapshot: ServiceSnapshot,
        *,
        now_monotonic: float,
        force: bool = False,
    ) -> None:
        payload = snapshot.as_topic_payload(self.topics)
        changed_keys = [
            key
            for key, value in payload.items()
            if self.last_published_state.get(key) != value
        ]
        if (
            not force
            and not changed_keys
            and now_monotonic - self.last_publish_monotonic < self.heartbeat_seconds
        ):
            return
        if (
            not force
            and not self._should_publish_now(payload, changed_keys, now_monotonic)
        ):
            return
        if (
            force
            or now_monotonic - self.last_publish_monotonic >= self.heartbeat_seconds
        ):
            publish_keys = list(payload)
        else:
            publish_keys = changed_keys
        for key in publish_keys:
            self.mqtt.publish(key, payload[key], retain=self.retain_state)
        self.last_published_state = payload
        self.last_publish_monotonic = now_monotonic

    def _should_publish_now(
        self,
        payload: dict[str, str],
        changed_keys: list[str],
        now_monotonic: float,
    ) -> bool:
        if now_monotonic - self.last_publish_monotonic >= self.heartbeat_seconds:
            return True
        immediate_keys = {
            self.topics.status_state,
            self.topics.stream_state,
            self.topics.classification_state,
        }
        if any(key in immediate_keys for key in changed_keys):
            return True
        previous_quality = self._parse_quality(
            self.last_published_state.get(self.topics.print_quality_state)
        )
        current_quality = self._parse_quality(payload[self.topics.print_quality_state])
        if previous_quality is None or current_quality is None:
            return False
        if (
            current_quality <= self.watch_quality_threshold
            and current_quality != previous_quality
        ):
            return True
        return previous_quality - current_quality >= self.rapid_quality_drop

    @staticmethod
    def _parse_quality(value: str | None) -> int | None:
        if value is None or value == "unknown":
            return None
        return int(value)
