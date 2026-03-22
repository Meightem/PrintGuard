import json
import logging
import os
import pickle
from dataclasses import dataclass
from typing import Any

import numpy as np
import onnxruntime as ort
from PIL import Image


LOGGER = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    label: str
    index: int
    distances: dict[str, float]


class ONNXClassifier:
    def __init__(self, model_path: str, options_path: str, prototypes_path: str):
        self.model_path = model_path
        self.options_path = options_path
        self.prototypes_path = prototypes_path
        self.session: ort.InferenceSession | None = None
        self.input_name: str | None = None
        self.output_name: str | None = None
        self.input_dims: list[int] | None = None
        self.prototypes: np.ndarray | None = None
        self.class_names: list[str] = []
        self.defect_idx: int = -1

    def load(self) -> None:
        self._validate_files()
        with open(self.options_path, "r", encoding="utf-8") as handle:
            model_options = json.load(handle)
        self.input_dims = list(map(int, model_options["model.x_dim"].split(",")))
        self.session = ort.InferenceSession(
            self.model_path,
            providers=["CPUExecutionProvider"],
        )
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        with open(self.prototypes_path, "rb") as handle:
            cache_data = pickle.load(handle)
        self.prototypes = np.asarray(cache_data["prototypes"], dtype=np.float32)
        self.class_names = list(cache_data["class_names"])
        self.defect_idx = int(cache_data.get("defect_idx", -1))
        LOGGER.info("Loaded ONNX model with classes: %s", ", ".join(self.class_names))

    def classify_frame(self, frame: np.ndarray) -> PredictionResult:
        if self.session is None or self.prototypes is None or self.input_name is None:
            raise RuntimeError("Classifier has not been loaded")
        input_array = self._preprocess_frame(frame)
        outputs = self.session.run([self.output_name], {self.input_name: input_array})
        embedding = np.asarray(outputs[0], dtype=np.float32).reshape(-1)
        distances = np.linalg.norm(self.prototypes - embedding, axis=1)
        index = int(np.argmin(distances))
        label = self.class_names[index]
        return PredictionResult(
            label=label,
            index=index,
            distances={name: float(distances[idx]) for idx, name in enumerate(self.class_names)},
        )

    def _preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        if not self.input_dims or len(self.input_dims) != 3:
            raise RuntimeError(f"Unsupported model input dims: {self.input_dims}")
        channels, crop_height, crop_width = self.input_dims
        if channels != 3:
            raise RuntimeError(f"Unsupported channel count: {channels}")
        image = Image.fromarray(frame[:, :, ::-1]).convert("L").convert("RGB")
        resize_size = 256
        image = self._resize_shortest_side(image, resize_size)
        image = self._center_crop(image, crop_width, crop_height)
        array = np.asarray(image, dtype=np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        array = (array - mean) / std
        array = np.transpose(array, (2, 0, 1))
        return np.expand_dims(array, axis=0).astype(np.float32)

    @staticmethod
    def _resize_shortest_side(image: Image.Image, shortest_side: int) -> Image.Image:
        width, height = image.size
        if width == 0 or height == 0:
            raise RuntimeError("Received empty frame")
        if width < height:
            new_width = shortest_side
            new_height = int(height * (shortest_side / width))
        else:
            new_height = shortest_side
            new_width = int(width * (shortest_side / height))
        return image.resize((new_width, new_height), Image.Resampling.BILINEAR)

    @staticmethod
    def _center_crop(image: Image.Image, crop_width: int, crop_height: int) -> Image.Image:
        width, height = image.size
        left = max((width - crop_width) // 2, 0)
        top = max((height - crop_height) // 2, 0)
        right = left + crop_width
        bottom = top + crop_height
        return image.crop((left, top, right, bottom))

    def _validate_files(self) -> None:
        for path in (self.model_path, self.options_path, self.prototypes_path):
            if not os.path.exists(path):
                raise FileNotFoundError(f"Required model artifact not found: {path}")
