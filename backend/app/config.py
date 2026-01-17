from pydantic_settings import BaseSettings
from pathlib import Path
import secrets

class Settings(BaseSettings):
    APP_NAME: str = "Jornais"
    DATABASE_URL: str = ""
    SECRET_KEY: str = "persistent-secret-key-jornais-2024-change-in-prod"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # File paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    STORAGE_DIR: Path = BASE_DIR / "storage"
    UPLOAD_DIR: Path = STORAGE_DIR / "uploads"
    THUMBNAIL_DIR: Path = STORAGE_DIR / "thumbnails"
    LOGS_DIR: Path = STORAGE_DIR / "logs"
    # DATA_DIR aliases STORAGE_DIR for flat structure (no more /storage/data/...)
    DATA_DIR: Path = STORAGE_DIR
    
    # Telegram bot integration
    TELEGRAM_DATA_DIR: str = ""
    GEMINI_API_KEY: str = ""
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields from environment

settings = Settings()

# Set default telegram data dir if not specified
if not settings.TELEGRAM_DATA_DIR:
    settings.TELEGRAM_DATA_DIR = str(settings.STORAGE_DIR)

# Ensure directories exist
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)
settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)

# Update database URL to use absolute path
settings.DATABASE_URL = f"sqlite:///{settings.DATA_DIR}/banca.db"
