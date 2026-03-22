from dataclasses import dataclass

from . import __version__
from .config import Settings


@dataclass(frozen=True)
class DiscoveryTopics:
    availability: str
    status_state: str
    stream_state: str
    classification_state: str
    print_quality_state: str


def build_topics(settings: Settings) -> DiscoveryTopics:
    base = settings.mqtt_topic_prefix
    return DiscoveryTopics(
        availability=f"{base}/availability",
        status_state=f"{base}/status/state",
        stream_state=f"{base}/stream/state",
        classification_state=f"{base}/classification/state",
        print_quality_state=f"{base}/print_quality/state",
    )


def publish_discovery(mqtt_client, settings: Settings, topics: DiscoveryTopics) -> None:
    device = {
        "identifiers": [settings.device_id],
        "name": settings.device_name,
        "manufacturer": "PrintGuard",
        "model": "MJPEG MQTT Monitor",
        "sw_version": __version__,
    }
    discovery_prefix = settings.mqtt_discovery_prefix
    entities = {
        f"{discovery_prefix}/binary_sensor/{settings.device_id}_stream/config": {
            "unique_id": f"{settings.device_id}_stream",
            "name": f"{settings.device_name} Stream",
            "state_topic": topics.stream_state,
            "payload_on": "ON",
            "payload_off": "OFF",
            "availability_topic": topics.availability,
            "payload_available": "online",
            "payload_not_available": "offline",
            "device_class": "connectivity",
            "device": device,
        },
        f"{discovery_prefix}/sensor/{settings.device_id}_classification/config": {
            "unique_id": f"{settings.device_id}_classification",
            "name": f"{settings.device_name} Classification",
            "state_topic": topics.classification_state,
            "availability_topic": topics.availability,
            "payload_available": "online",
            "payload_not_available": "offline",
            "icon": "mdi:printer-3d-nozzle-alert",
            "device": device,
        },
        f"{discovery_prefix}/sensor/{settings.device_id}_print_quality/config": {
            "unique_id": f"{settings.device_id}_print_quality",
            "name": f"{settings.device_name} Print Quality",
            "state_topic": topics.print_quality_state,
            "availability_topic": topics.availability,
            "payload_available": "online",
            "payload_not_available": "offline",
            "icon": "mdi:printer-3d-nozzle",
            "device": device,
        },
        f"{discovery_prefix}/sensor/{settings.device_id}_status/config": {
            "unique_id": f"{settings.device_id}_status",
            "name": f"{settings.device_name} Status",
            "state_topic": topics.status_state,
            "availability_topic": topics.availability,
            "payload_available": "online",
            "payload_not_available": "offline",
            "icon": "mdi:state-machine",
            "device": device,
        },
    }
    for topic, payload in entities.items():
        mqtt_client.publish(topic, payload, retain=settings.mqtt_retain_discovery)
