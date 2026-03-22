from dataclasses import dataclass
from enum import StrEnum

from .home_assistant import DiscoveryTopics


class ServiceStatus(StrEnum):
    STARTING = "starting"
    ONLINE = "online"
    OFFLINE = "offline"


class StreamState(StrEnum):
    ON = "ON"
    OFF = "OFF"


class ClassificationState(StrEnum):
    UNKNOWN = "unknown"
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass(frozen=True)
class ServiceSnapshot:
    status: ServiceStatus = ServiceStatus.STARTING
    stream: StreamState = StreamState.OFF
    classification: ClassificationState = ClassificationState.UNKNOWN
    print_quality: str = "unknown"

    def as_topic_payload(self, topics: DiscoveryTopics) -> dict[str, str]:
        return {
            topics.status_state: self.status.value,
            topics.stream_state: self.stream.value,
            topics.classification_state: self.classification.value,
            topics.print_quality_state: self.print_quality,
        }
