from facial_portal.app import create_app
from facial_portal.config import Settings
from facial_portal.service import RecognitionService
from waitress import serve


if __name__ == "__main__":
    settings = Settings.load()
    service = RecognitionService(settings)
    app = create_app(settings, service)
    service.start_background()
    serve(app, host=settings.host, port=settings.port)
