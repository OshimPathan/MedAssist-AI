"""
MedAssist AI - Configuration Management
Environment variables and application settings
"""

import os
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional, List


class Settings(BaseSettings):
    """Application configuration settings"""
    
    # Application
    APP_NAME: str = "MedAssist AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "mongodb://localhost:27017/medassist_db"
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    
    # Security
    SECRET_KEY: str = "change-me-in-production-use-a-strong-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # AI & LLM
    OPENAI_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gpt-4-turbo-preview"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    MAX_TOKENS: int = 1000
    TEMPERATURE: float = 0.7
    
    # Vector Database
    FAISS_INDEX_PATH: str = "./data/faiss_index"
    
    # Emergency Settings
    EMERGENCY_PHONE: str = "108"
    EMERGENCY_EMAIL: str = "emergency@hospital.com"
    
    # Notifications
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None
    
    # WhatsApp (Twilio)
    WHATSAPP_NUMBER: Optional[str] = None
    
    # Email (SMTP)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # CORS (comma-separated string in .env)
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    
    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
    
    class Config:
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


# Singleton instance
settings = Settings()

