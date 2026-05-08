# Location: /src/core/config.py
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Always load the project root .env file explicitly.
ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

class Settings(BaseSettings):
    """
    Application settings
    """
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "myuser")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "mypassword")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "resume_parser_db")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "db")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")

    # Construct the database URL
    @property
    def DATABASE_URL(self) -> str:
        # For local development, use SQLite
        return "sqlite:///./resume_parser.db"

    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

    # --- THIS IS THE LINE THAT WAS MISSING ---
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")


# Create a single instance of the settings to be imported by other files
settings = Settings()