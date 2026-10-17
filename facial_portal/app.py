from __future__ import annotations

from flask import Flask, jsonify, request, render_template

from .config import Settings
from .service import RecognitionService


def _authorized(settings: Settings, request) -> bool:
    return not settings.api_token or request.headers.get("X-API-Key", "") == settings.api_token


def create_app(settings: Settings | None = None, service: RecognitionService | None = None) -> Flask:
    settings = settings or Settings.load()
    service = service or RecognitionService(settings)
    app = Flask(__name__)
    app.config["facial_service"] = service

    @app.get("/admin")
    def admin():
        return render_template("admin.html", model_id=settings.recognition.model_id, drive_folder_url=settings.selfie_drive_folder_url, api_token_configured=bool(settings.api_token))

    @app.get("/healthz")
    def healthz():
        return jsonify({"ok": True, "service": "facial-portal", "version": "0.1.0"})

    @app.get("/api/status")
    def status():
        return jsonify({"frames": service.frame_count, "identities": len(service.store.identities), "last_event": service.last_event, "last_error": service.last_error, "gate_physical_enabled": settings.gate.enabled and settings.gate.allow_physical})

    @app.get("/api/audit")
    def audit():
        return jsonify(service.audit.recent(min(int(request.args.get("limit", 50)), 200)))

    @app.post("/api/whitelist/refresh")
    def refresh():
        if not _authorized(settings, request):
            return jsonify({"error": "unauthorized"}), 401
        return jsonify({"identities": service.refresh_whitelist()})

    @app.post("/api/enroll")
    def enroll():
        if not _authorized(settings, request):
            return jsonify({"error": "unauthorized"}), 401
        upload = request.files.get("selfie")
        if upload is None or not upload.filename:
            return jsonify({"error": "selfie is required"}), 400
        import cv2
        import numpy as np
        selfie_bytes = upload.read()
        frame = cv2.imdecode(np.frombuffer(selfie_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            return jsonify({"error": "invalid image"}), 400
        try:
            return jsonify(service.enroll(frame, request.form.get("person_id", ""), request.form.get("name", ""), selfie_bytes, upload.mimetype))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    @app.post("/api/gate/pulse")
    def pulse():
        if not _authorized(settings, request):
            return jsonify({"error": "unauthorized"}), 401
        opened, detail = service.gate.pulse("manual_api")
        service.audit.record("gate_pulse_requested", detail=detail)
        return jsonify({"opened": opened, "detail": detail}), (200 if opened else 409)

    return app
