from dataclasses import dataclass

from . import __version__
from .config import Settings


@dataclass(frozen=True)
class DiscoveryTopics:
    availability: str
    status_state: str
    stream_state: str
    classification_state: str
    classification_confidence_state: str
    failure_confidence_state: str
    severity_state: str
    defect_state: str
    error_state: str
    last_inference_ts_state: str
    enabled_state: str
    enabled_set: str


def build_topics(settings: Settings) -> DiscoveryTopics:
    base = settings.mqtt_topic_prefix
    return DiscoveryTopics(
        availability=f"{base}/availability",
        status_state=f"{base}/status/state",
        stream_state=f"{base}/stream/state",
        classification_state=f"{base}/classification/state",
        classification_confidence_state=f"{base}/classification_confidence/state",
        failure_confidence_state=f"{base}/failure_confidence/state",
        severity_state=f"{base}/severity/state",
        defect_state=f"{base}/defect/state",
        error_state=f"{base}/error/state",
        last_inference_ts_state=f"{base}/last_inference_ts/state",
        enabled_state=f"{base}/enabled/state",
        enabled_set=f"{base}/enabled/set",
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
        f"{discovery_prefix}/sensor/{settings.device_id}_classification_confidence/config": {
            "unique_id": f"{settings.device_id}_classification_confidence",
            "name": f"{settings.device_name} Classification Confidence",
            "state_topic": topics.classification_confidence_state,
            "availability_topic": topics.availability,
            "payload_available": "online",
            "payload_not_available": "offline",
            "unit_of_measurement": "%",
            "icon": "mdi:percent-outline",
            "device": device,
        },
        f"{discovery_prefix}/sensor/{settings.device_id}_failure_confidence/config": {
            "unique_id": f"{settings.device_id}_failure_confidence",
            "name": f"{settings.device_name} Failure Confidence",
            "state_topic": topics.failure_confidence_state,
            "availability_topic": topics.availability,
            "payload_available": "online",
            "payload_not_available": "offline",
            "unit_of_measurement": "%",
            "icon": "mdi:alert-decagram-outline",
            "device": device,
        },
        f"{discovery_prefix}/sensor/{settings.device_id}_severity/config": {
            "unique_id": f"{settings.device_id}_severity",
            "name": f"{settings.device_name} Severity",
            "state_topic": topics.severity_state,
            "availability_topic": topics.availability,
            "payload_available": "online",
            "payload_not_available": "offline",
            "icon": "mdi:alert-outline",
            "device": device,
        },
        f"{discovery_prefix}/binary_sensor/{settings.device_id}_defect/config": {
            "unique_id": f"{settings.device_id}_defect",
            "name": f"{settings.device_name} Defect",
            "state_topic": topics.defect_state,
            "payload_on": "ON",
            "payload_off": "OFF",
            "availability_topic": topics.availability,
            "payload_available": "online",
            "payload_not_available": "offline",
            "device_class": "problem",
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
        f"{discovery_prefix}/sensor/{settings.device_id}_last_error/config": {
            "unique_id": f"{settings.device_id}_last_error",
            "name": f"{settings.device_name} Last Error",
            "state_topic": topics.error_state,
            "availability_topic": topics.availability,
            "payload_available": "online",
            "payload_not_available": "offline",
            "icon": "mdi:alert-circle-outline",
            "device": device,
        },
        f"{discovery_prefix}/sensor/{settings.device_id}_last_inference_ts/config": {
            "unique_id": f"{settings.device_id}_last_inference_ts",
            "name": f"{settings.device_name} Last Inference",
            "state_topic": topics.last_inference_ts_state,
            "availability_topic": topics.availability,
            "payload_available": "online",
            "payload_not_available": "offline",
            "icon": "mdi:clock-outline",
            "device": device,
        },
        f"{discovery_prefix}/switch/{settings.device_id}_enabled/config": {
            "unique_id": f"{settings.device_id}_enabled",
            "name": f"{settings.device_name} Enabled",
            "state_topic": topics.enabled_state,
            "command_topic": topics.enabled_set,
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "availability_topic": topics.availability,
            "payload_available": "online",
            "payload_not_available": "offline",
            "icon": "mdi:toggle-switch-outline",
            "device": device,
        },
    }
    for topic, payload in entities.items():
        mqtt_client.publish(topic, payload, retain=settings.mqtt_retain_discovery)
