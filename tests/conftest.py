import pytest

from app import create_app
from config import Config
from models import db


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    GEMINI_API_KEY = "test-key"


def fake_prediction(date_of_birth, glucose, haemoglobin, cholesterol, **_kwargs):
    """Stands in for the Gemini call so tests run offline and give predictable results."""
    risk = "High" if glucose >= 200 or cholesterol >= 240 else "Low"
    return {"risk_level": risk, "remarks": f"Test prediction: {risk} risk."}


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr("routes.predict_health_risk", fake_prediction)
    app = create_app(TestingConfig)
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()
