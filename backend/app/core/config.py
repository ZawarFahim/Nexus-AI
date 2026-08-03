from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Nexus AI"
    API_V1_STR: str = "/api/v1"
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # Database Configuration
    DATABASE_URL: str = "postgresql+asyncpg://nexus_user:nexus_pass@localhost:5432/nexus_db"
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Qdrant Configuration
    QDRANT_URL: str = "http://localhost:6333"

    # JWT Authentication Configuration
    SECRET_KEY: str = "supersecretkey_please_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # OAuth and Security
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    # Fernet encryption key must be 32 url-safe base64-encoded bytes. 
    # e.g. generated via cryptography.fernet.Fernet.generate_key()
    ENCRYPTION_KEY: str = "xU22r5lXq8z4G_qj4G8f1cZ-Qc2Y3G_kZ9xV5pL8rX8=" 

    # AI Configuration
    GEMINI_API_KEY: str = ""

    # Tools Configuration
    GITHUB_ACCESS_TOKEN: str = ""
    N8N_BASE_URL: str = "http://localhost:5678"
    N8N_API_KEY: str = ""





    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True)

settings = Settings()
