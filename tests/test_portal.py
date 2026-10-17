import json

import numpy as np

from facial_portal.app import create_app
from facial_portal.config import GateConfig, Settings
from facial_portal.embeddings import parse_embedding
from facial_portal.service import RecognitionService
from facial_portal.whitelist import WhitelistStore


def test_parse_embedding_normalizes():
    vector = parse_embedding("1,0")
    assert vector.tolist() == [1.0, 0.0]


def test_health_and_gate_are_safe_by_default(tmp_path):
    settings = Settings(data_dir=str(tmp_path), gate=GateConfig(), api_token="test-token")
    service = RecognitionService(settings)
    client = create_app(settings, service).test_client()
    assert client.get("/healthz").status_code == 200
    response = client.post("/api/gate/pulse", headers={"X-API-Key": "test-token"})
    assert response.status_code == 409
    assert response.json["opened"] is False


def test_mutating_api_is_open_when_token_is_not_configured(tmp_path):
    settings = Settings(data_dir=str(tmp_path), gate=GateConfig())
    client = create_app(settings, RecognitionService(settings)).test_client()
    response = client.post("/api/gate/pulse")
    assert response.status_code == 409


def test_config_round_trip(tmp_path):
    settings = Settings(data_dir=str(tmp_path))
    path = tmp_path / "config.json"
    settings.save(path)
    loaded = Settings.load(path)
    assert json.loads(path.read_text())["gate"]["allow_physical"] is False
    assert loaded.data_dir == str(tmp_path)


def test_whitelist_csv_is_cached_without_real_identity_data(tmp_path):
    source = tmp_path / "source.csv"
    source.write_text("person_id,name,embedding,active\nunit,Unit Test,1;0,true\n", encoding="utf-8")
    store = WhitelistStore(tmp_path / "cache.json", "test-model")
    assert store.refresh(str(source)) == 1
    assert store.identities[0].person_id == "unit"
    assert store.load_cache() == 1


def test_whitelist_cache_rejects_a_different_model(tmp_path):
    source = tmp_path / "source.csv"
    source.write_text("person_id,name,embedding,active\nunit,Unit Test,1;0,true\n", encoding="utf-8")
    from facial_portal.whitelist import WhitelistStore
    cache = tmp_path / "cache.json"
    WhitelistStore(cache, "model-a").refresh(str(source))
    try:
        WhitelistStore(cache, "model-b").load_cache()
    except ValueError as exc:
        assert "different embedding model" in str(exc)
    else:
        raise AssertionError("model mismatch was not rejected")


def test_authorization_requires_stable_hits_and_obeys_cooldown(tmp_path, monkeypatch):
    settings = Settings(data_dir=str(tmp_path))
    settings.camera.process_every_n = 1
    settings.recognition.stable_hits = 2
    settings.recognition.cooldown_seconds = 60
    service = RecognitionService(settings)
    service.store.identities = []
    identity_feature = parse_embedding("1,0")
    from facial_portal.embeddings import Identity
    service.store.identities = [Identity("unit", "Unit Test", identity_feature)]
    service.engine.embed = lambda frame: [identity_feature]
    service.engine.similarity = lambda left, right: 0.9
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    assert service.process_frame(frame)["status"] == "pending"
    assert service.process_frame(frame)["status"] == "authorized"
    assert service.process_frame(frame)["status"] == "cooldown"


def test_superadmin_enrollment_from_selfie(tmp_path):
    settings = Settings(data_dir=str(tmp_path), api_token="test-token")
    service = RecognitionService(settings)
    feature = parse_embedding("1,0")
    service.engine.embed = lambda frame: [feature]
    client = create_app(settings, service).test_client()
    import cv2
    from io import BytesIO
    selfie = cv2.imencode(".jpg", np.zeros((100, 100, 3), dtype=np.uint8))[1].tobytes()
    response = client.post("/api/enroll", data={"person_id": "unit", "name": "Unit Test", "selfie": (BytesIO(selfie), "selfie.jpg")}, headers={"X-API-Key": "test-token"}, content_type="multipart/form-data")
    assert response.status_code == 200
    assert response.json["model_id"] == settings.recognition.model_id
    assert response.json["sheet_sync"] == "local_only"
