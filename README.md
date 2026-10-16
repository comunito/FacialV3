# Comunito FacialV3

Portal autónomo de control de acceso facial para Raspberry Pi 5 (4 GB), con cámara Tapo C320WS por RTSP/Wi-Fi.

La rama `dev/facial-portal-rebuild` contiene el portal nuevo. El archivo histórico `portal_face_full.py` se conserva únicamente como referencia durante la migración.

## Arquitectura

- `facial_portal/embeddings.py`: YuNet + SFace de OpenCV, adecuados para inferencia local sin enviar imágenes a la nube.
- `facial_portal/whitelist.py`: whitelist local en caché JSON, con fuente CSV local o URL compatible con Google Sheets publicado.
- `facial_portal/audit.py`: bitácora SQLite local.
- `facial_portal/gate.py`: integración HTTP con ESP32; permanece en dry-run por defecto.
- `facial_portal/service.py`: captura RTSP, reconocimiento y coordinación de eventos.
- `facial_portal/app.py`: health, estado, bitácora y refresh de whitelist.
- `models/README.md`: política de perfiles, compatibilidad y versionado de modelos.

## Arranque local

```bash
cp config.example.json config.json
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pytest -q
python main.py
```

No se incluyen claves, contraseñas, fotos ni embeddings reales. `data/whitelist.csv` y `config.json` están ignorados por Git.

Configura `api_token` con un valor aleatorio largo o usa `FACIAL_API_TOKEN`; las operaciones de refresh y gate requieren `X-API-Key`.

## Seguridad del gate

`gate.enabled` y `gate.allow_physical` son `false` en la configuración de ejemplo. Mientras cualquiera de ellos sea falso, cualquier solicitud devuelve `dry-run` y no se envía ninguna orden al ESP32.

## Formato de whitelist

CSV con columnas `person_id,name,embedding,active`. Los embeddings se generan en el laboratorio de `core` y se sincronizan después mediante una fuente autenticada o un mecanismo seguro acordado. Los embeddings reales no deben subirse a GitHub.

El contrato de esa integración está documentado en [`docs/core-embeddings-contract.md`](docs/core-embeddings-contract.md); la implementación dentro de `core` queda como fase separada.
