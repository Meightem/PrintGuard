from printguard.home_assistant import build_topics, publish_discovery
from tests.helpers import make_settings


class RecordingPublisher:
    def __init__(self) -> None:
        self.messages: list[tuple[str, dict, bool]] = []

    def publish(self, topic: str, payload: str | dict, retain: bool = True) -> None:
        if not isinstance(payload, dict):
            raise AssertionError("discovery payloads must be dictionaries")
        self.messages.append((topic, payload, retain))


def test_build_topics_uses_topic_prefix() -> None:
    settings = make_settings(mqtt_topic_prefix="custom/prefix")

    topics = build_topics(settings)

    assert topics.availability == "custom/prefix/availability"
    assert topics.print_quality_state == "custom/prefix/print_quality/state"


def test_publish_discovery_emits_expected_entities() -> None:
    settings = make_settings()
    topics = build_topics(settings)
    publisher = RecordingPublisher()

    publish_discovery(publisher, settings, topics)

    published = {topic: payload for topic, payload, _retain in publisher.messages}
    assert len(published) == 4
    stream_topic = (
        f"{settings.mqtt_discovery_prefix}/binary_sensor/"
        f"{settings.device_id}_stream/config"
    )
    stream_payload = published[stream_topic]
    assert stream_payload["availability_topic"] == topics.availability
    assert stream_payload["device"]["name"] == settings.device_name
    assert all(retain for _topic, _payload, retain in publisher.messages)
