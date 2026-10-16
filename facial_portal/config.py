from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class CameraConfig:
    name: str = "tapo-c320ws"
    rtsp_url: str = ""
    process_every_n: int = 2
    resize_width: int = 960


@dataclass
class RecognitionConfig:
    model_id: str = "sface-2021dec-fp32-v1"
    threshold: float = 0.363
    stable_hits: int = 2
    cooldown_seconds: float = 8.0
    detector_model: str = "models/face_detection_yunet.onnx"
    recognizer_model: str = "models/face_recognition_sface.onnx"


@dataclass
class GateConfig:
    enabled: bool = False
    mode: str = "http"
    url: str = ""
    token: str = ""
    pulse_ms: int = 500
    allow_physical: bool = False


@dataclass
class Settings:
    host: str = "0.0.0.0"
    port: int = 5001
    timezone: str = "America/Mexico_City"
    data_dir: str = "data"
    api_token: str = ""
    camera: CameraConfig = field(default_factory=CameraConfig)
    recognition: RecognitionConfig = field(default_factory=RecognitionConfig)
    gate: GateConfig = field(default_factory=GateConfig)
    whitelist_source: str = ""
    webhook_urls: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: str | Path = "config.json") -> "Settings":
        path = Path(path)
        raw: dict = {}
        if path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
        camera = CameraConfig(**{**asdict(CameraConfig()), **raw.get("camera", {})})
        recognition = RecognitionConfig(**{**asdict(RecognitionConfig()), **raw.get("recognition", {})})
        gate = GateConfig(**{**asdict(GateConfig()), **raw.get("gate", {})})
        values = {k: v for k, v in raw.items() if k not in {"camera", "recognition", "gate"}}
        settings = cls(camera=camera, recognition=recognition, gate=gate, **values)
        settings.camera.rtsp_url = os.environ.get("FACIAL_RTSP_URL", settings.camera.rtsp_url)
        settings.api_token = os.environ.get("FACIAL_API_TOKEN", settings.api_token)
        return settings

    def save(self, path: str | Path = "config.json") -> None:
        Path(path).write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
