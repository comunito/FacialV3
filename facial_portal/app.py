from __future__ import annotations

from flask import Flask, jsonify, request

from .config import Settings
from .service import RecognitionService


def create_app(settings: Settings | None = None, service: RecognitionService | None = None) -> Flask:
    settings = settings or Settings.load()
    service = service or RecognitionService(settings)
    app = Flask(__name__)
    app.config["facial_service"] = service

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
        return jsonify({"identities": service.refresh_whitelist()})

    @app.post("/api/gate/pulse")
    def pulse():
        opened, detail = service.gate.pulse("manual_api")
        service.audit.record("gate_pulse_requested", detail=detail)
        return jsonify({"opened": opened, "detail": detail}), (200 if opened else 409)

    return app
