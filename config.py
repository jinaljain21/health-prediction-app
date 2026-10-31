import os

from dotenv import load_dotenv

# Read settings (including the API key) from a local .env file, which is never committed
load_dotenv()


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///health.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    AI_TIMEOUT_SECONDS = int(os.getenv("AI_TIMEOUT_SECONDS", "30"))
    AI_CALLS_PER_MINUTE = int(os.getenv("AI_CALLS_PER_MINUTE", "10"))

    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
