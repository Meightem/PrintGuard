from printguard.domain import (
    ClassificationState,
    ServiceSnapshot,
    ServiceStatus,
    StreamState,
)
from printguard.home_assistant import build_topics
from printguard.state import MQTTStatePublisher
from tests.helpers import make_settings


class RecordingMQTT:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str, bool]] = []

    def publish(self, topic: str, payload: str, retain: bool = True) -> None:
        self.messages.append((topic, payload, retain))


def test_state_publisher_skips_unchanged_snapshot_before_heartbeat() -> None:
    mqtt = RecordingMQTT()
    topics = build_topics(make_settings())
    publisher = MQTTStatePublisher(mqtt, topics, retain_state=True)
    snapshot = ServiceSnapshot(
        status=ServiceStatus.ONLINE,
        stream=StreamState.ON,
        classification=ClassificationState.SUCCESS,
        print_quality="8",
    )

    publisher.publish(snapshot, now_monotonic=100.0, force=True)
    first_publish_count = len(mqtt.messages)
    publisher.publish(snapshot, now_monotonic=101.0)

    assert len(mqtt.messages) == first_publish_count
