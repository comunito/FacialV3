from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass(frozen=True)
class Identity:
    person_id: str
    name: str
    embedding: np.ndarray
    active: bool = True


def parse_embedding(value: str | list[float]) -> np.ndarray:
    if isinstance(value, str):
        value = value.strip()
        if value.startswith("["):
            value = json.loads(value)
        else:
            value = [float(x) for x in value.replace(";", ",").split(",") if x.strip()]
    vector = np.asarray(value, dtype=np.float32).reshape(-1)
    if vector.size == 0:
        raise ValueError("empty embedding")
    norm = np.linalg.norm(vector)
    return vector / norm if norm else vector


class FaceEngine:
    """OpenCV YuNet + SFace engine; models are loaded only when first used."""

    def __init__(self, detector_path: str, recognizer_path: str):
        self.detector_path = Path(detector_path)
        self.recognizer_path = Path(recognizer_path)
        self._detector = None
        self._recognizer = None
        self.feature_dim = None

    @property
    def embedding_dim(self) -> int | None:
        if self._recognizer is None:
            return None
        return int(self.feature_dim)

    def _load(self) -> None:
        if self._detector is not None:
            return
        if not self.detector_path.exists() or not self.recognizer_path.exists():
            raise FileNotFoundError("face model files are missing")
        self._detector = cv2.FaceDetectorYN.create(str(self.detector_path), "", (320, 320), 0.8, 0.3, 5000)
        self._recognizer = cv2.FaceRecognizerSF.create(str(self.recognizer_path), "")

    def embed(self, frame: np.ndarray) -> list[np.ndarray]:
        self._load()
        height, width = frame.shape[:2]
        self._detector.setInputSize((width, height))
        _, faces = self._detector.detect(frame)
        if faces is None:
            return []
        result = []
        for face in faces:
            aligned = self._recognizer.alignCrop(frame, face)
            feature = self._recognizer.feature(aligned).reshape(-1).astype(np.float32)
            self.feature_dim = feature.size
            result.append(parse_embedding(feature.tolist()))
        return result

    def similarity(self, left: np.ndarray, right: np.ndarray) -> float:
        self._load()
        return float(self._recognizer.match(left.reshape(1, -1), right.reshape(1, -1), cv2.FaceRecognizerSF_FR_COSINE))
