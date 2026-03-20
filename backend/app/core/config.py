from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # App
    APP_NAME: str = "KazBuildOS"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Система автоматизации сопровождения строительных проектов РК"
    DEBUG: bool = False
    SECRET_KEY: str = "kazbuildos-secret-key-change-in-production"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./kazbuildos.db"

    # Anthropic Claude API
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL: str = "claude-sonnet-4-6"

    # Offline mode
    OFFLINE_MODE: bool = False

    # Document storage
    DOCS_STORAGE_PATH: str = "./storage/documents"
    TEMPLATES_PATH: str = "./app/templates/docx"

    # Company info
    COMPANY_NAME: str = "KazBuildOS Systems"
    COMPANY_BIN: str = "000000000000"  # БИН организации
    COMPANY_ADDRESS: str = "г. Алматы, Республика Казахстан"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
