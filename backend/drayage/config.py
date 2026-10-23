"""
Configuration settings for Component 2: Intelligent Drayage Truck Optimization System.
Loads environment variables safely via pydantic-settings.
"""
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings

_CURRENT_DIR = Path(__file__).resolve().parent


class DrayageSettings(BaseSettings):
    PROJECT_NAME: str = "Component 2: Intelligent Drayage Truck Optimization Backend"
    API_V1_PREFIX: str = "/api/v1"
    
    # PostgreSQL Configuration
    # Uses local port 5432 and default database smart_port_management
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/smart_port_management"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_CONNECT_TIMEOUT_SECONDS: int = 3
    
    # JWT & Authentication Security
    # In production, JWT_SECRET should be supplied via environment variable
    JWT_SECRET: str = "drayage_port_optimization_jwt_secret_key_2026_super_secure"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12  # 12-hour terminal shift
    
    # Server & Networking
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = ["*"]
    
    # Operational Mode
    ENVIRONMENT: str = "development"
    USE_IN_MEMORY_FALLBACK_IF_DB_UNAVAILABLE: bool = True

    model_config = {
        "env_file": [
            ".env",
            "backend/drayage/.env",
            str(_CURRENT_DIR / ".env"),
        ],
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = DrayageSettings()
