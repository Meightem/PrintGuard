from collections import deque
from dataclasses import dataclass

from .domain import ClassificationState
from .model import PredictionResult


@dataclass(frozen=True)
class ClassificationOutcome:
    classification: ClassificationState
    print_quality: str
    failure_confidence: float


class ClassificationPolicy:
    def __init__(
        self,
        *,
        quality_smoothing_alpha: float = 0.35,
        defect_voting_window: int = 5,
        defect_voting_threshold: int = 2,
    ) -> None:
        self.quality_smoothing_alpha = quality_smoothing_alpha
        self.defect_voting_threshold = defect_voting_threshold
        self._recent_raw_labels: deque[str] = deque(maxlen=defect_voting_window)
        self._smoothed_failure_confidence: float | None = None

    def reset(self) -> None:
        self._recent_raw_labels.clear()
        self._smoothed_failure_confidence = None

    def observe(self, prediction: PredictionResult) -> ClassificationOutcome:
        self._recent_raw_labels.append(prediction.label)
        classification = self._confirm_classification(prediction.label)
        smoothed_failure_confidence = self._smooth_failure_confidence(
            prediction.failure_confidence
        )
        self._smoothed_failure_confidence = smoothed_failure_confidence
        return ClassificationOutcome(
            classification=classification,
            print_quality=str(
                self._failure_confidence_to_quality(smoothed_failure_confidence)
            ),
            failure_confidence=smoothed_failure_confidence,
        )

    def _smooth_failure_confidence(self, failure_confidence: float) -> float:
        if self._smoothed_failure_confidence is None:
            return failure_confidence
        return (
            self.quality_smoothing_alpha * failure_confidence
            + (1.0 - self.quality_smoothing_alpha) * self._smoothed_failure_confidence
        )

    def _confirm_classification(self, raw_label: str) -> ClassificationState:
        if raw_label != ClassificationState.FAILURE.value:
            return ClassificationState.SUCCESS
        failure_votes = sum(
            1
            for label in self._recent_raw_labels
            if label == ClassificationState.FAILURE.value
        )
        if failure_votes >= self.defect_voting_threshold:
            return ClassificationState.FAILURE
        return ClassificationState.SUCCESS

    @staticmethod
    def _failure_confidence_to_quality(failure_confidence: float) -> int:
        thresholds = [0.95, 0.85, 0.75, 0.65, 0.55, 0.45, 0.35, 0.25, 0.15]
        for index, threshold in enumerate(thresholds, start=1):
            if failure_confidence >= threshold:
                return index
        return 10
