from __future__ import annotations

import time
import threading
from collections import defaultdict
from datetime import datetime, timezone

import cv2
import requests

from .audit import AuditLog
from .config import Settings
from .embeddings import FaceEngine
from .gate import Gate
from .webhooks import send
from .whitelist import WhitelistStore


class RecognitionService:
    def __init__(self, settings: Settings):
        self.settings = settings
        data = settings.data_dir
        self.audit = AuditLog(f"{data}/audit.sqlite3")
        self.store = WhitelistStore(f"{data}/whitelist.json", settings.recognition.model_id)
        self.engine = FaceEngine(settings.recognition.detector_model, settings.recognition.recognizer_model)
        self.gate = Gate(settings.gate)
        self.frame_count = 0
        self.last_event = None
        self.last_error = ""
        self._worker = None
        self._candidate_hits = defaultdict(int)
        self._last_authorized_at = 0.0
        self.store.load_cache()

    def refresh_whitelist(self) -> int:
        count = self.store.refresh(self.settings.whitelist_source)
        self.audit.record("whitelist_refreshed", detail=f"identities={count}")
        return count

    def enroll(self, frame, person_id: str, name: str) -> dict:
        person_id = person_id.strip()
        name = name.strip()
        if not person_id or not name:
            raise ValueError("person_id and name are required")
        features = self.engine.embed(self._resize_for_inference(frame))
        if len(features) != 1:
            raise ValueError("the selfie must contain exactly one face")
        count = self.store.upsert(person_id, name, features[0])
        self.audit.record("face_enrolled", person_id=person_id, name=name, detail=f"model={self.settings.recognition.model_id}")
        webhook_error = ""
        if self.settings.embedding_webhook_url:
            try:
                response = requests.post(self.settings.embedding_webhook_url, json={"person_id": person_id, "name": name, "embedding": features[0].tolist(), "model_id": self.settings.recognition.model_id}, timeout=10)
                response.raise_for_status()
            except requests.RequestException as exc:
                webhook_error = exc.__class__.__name__
                self.audit.record("face_enrollment_sync_error", person_id=person_id, name=name, detail=webhook_error)
        return {"person_id": person_id, "name": name, "model_id": self.settings.recognition.model_id, "identities": count, "sheet_sync": "sent" if self.settings.embedding_webhook_url and not webhook_error else ("error" if webhook_error else "local_only"), "sheet_sync_error": webhook_error}

    def process_frame(self, frame) -> dict:
        self.frame_count += 1
        if self.frame_count % max(1, self.settings.camera.process_every_n):
            return {"status": "skipped"}
        frame = self._resize_for_inference(frame)
        features = self.engine.embed(frame)
        if not features:
            return {"status": "no_face"}
        identity, score = self.store.match(features[0], self.engine.similarity)
        threshold = self.settings.recognition.threshold
        if identity is None or score < threshold:
            self.audit.record("face_denied", score=score)
            return {"status": "denied", "score": score}
        self._candidate_hits[identity.person_id] += 1
        if self._candidate_hits[identity.person_id] < max(1, self.settings.recognition.stable_hits):
            return {"status": "pending", "person_id": identity.person_id, "score": score}
        now = time.monotonic()
        if now - self._last_authorized_at < max(0.0, self.settings.recognition.cooldown_seconds):
            return {"status": "cooldown", "person_id": identity.person_id, "score": score}
        self._last_authorized_at = now
        self.audit.record("face_authorized", identity.person_id, identity.name, score)
        self.last_event = datetime.now(timezone.utc).isoformat()
        opened, gate_detail = self.gate.pulse(identity.person_id)
        errors = send(self.settings.webhook_urls, {"event": "face_authorized", "person_id": identity.person_id, "name": identity.name, "score": score, "gate_opened": opened})
        return {"status": "authorized", "person_id": identity.person_id, "name": identity.name, "score": score, "gate": gate_detail, "webhook_errors": errors}

    def _resize_for_inference(self, frame):
        width = max(0, int(self.settings.camera.resize_width))
        if not width or frame.shape[1] <= width:
            return frame
        ratio = width / frame.shape[1]
        height = max(1, int(frame.shape[0] * ratio))
        return cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)

    def run(self) -> None:
        url = self.settings.camera.rtsp_url
        if not url:
            raise RuntimeError("camera.rtsp_url is empty")
        capture = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        if not capture.isOpened():
            raise RuntimeError("could not open RTSP camera")
        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    time.sleep(1)
                    capture.release()
                    capture = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
                    continue
                self.process_frame(frame)
        finally:
            capture.release()

    def start_background(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._worker = threading.Thread(target=self._run_guarded, name="facial-camera", daemon=True)
        self._worker.start()

    def _run_guarded(self) -> None:
        try:
            self.run()
        except Exception as exc:
            self.last_error = str(exc)
            self.audit.record("camera_error", detail=exc.__class__.__name__)
