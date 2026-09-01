"""Runtime configuration loaded exclusively from the environment."""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


class Config:
    """Configuration shared by the production application."""

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"

    @classmethod
    def validate(cls):
        missing = [
            name
            for name, value in {
                "DATABASE_URL": cls.SQLALCHEMY_DATABASE_URI,
                "SECRET_KEY": cls.SECRET_KEY,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(
                "Missing required environment variable(s): " + ", ".join(missing)
            )
