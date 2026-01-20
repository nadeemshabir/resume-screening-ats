"""
Configuration Management
Handles all environment variables and app settings
"""
from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # App Info
    APP_NAME: str = "Resume Screening API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # API Keys
    GROQ_API_KEY: str
    
    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS Settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
    ]
    
    # File Upload Settings
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".docx", ".doc", ".jpg", ".jpeg", ".png"]
    UPLOAD_DIR: str = "uploads"
    
    # OCR Settings
    TESSERACT_CMD: str = ""  # Set if Tesseract not in PATH
    OCR_ENABLED: bool = True
    
    # Groq Settings
    GROQ_MODEL: str = "llama-3.1-70b-versatile"  # Best for reasoning
    GROQ_TEMPERATURE: float = 0.3  # Lower = more consistent
    GROQ_MAX_TOKENS: int = 2000
    
    # Database Settings
    DATABASE_URL: str = "sqlite:///./resume_screening.db"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 30
    
    # Scoring Weights (must sum to 1.0)
    SKILLS_WEIGHT: float = 0.40
    EXPERIENCE_WEIGHT: float = 0.30
    EDUCATION_WEIGHT: float = 0.20
    KEYWORDS_WEIGHT: float = 0.10
    
    # Google API Settings
    GOOGLE_CREDENTIALS_PATH: str = "credentials.json"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance
    Using lru_cache ensures we only load settings once
    """
    return Settings()


# Export settings instance
settings = get_settings()


# Validation on startup
def validate_settings():
    """Validate critical settings on app startup"""
    errors = []
    
    if not settings.GROQ_API_KEY:
        errors.append("GROQ_API_KEY is required")
    
    weights_sum = (
        settings.SKILLS_WEIGHT + 
        settings.EXPERIENCE_WEIGHT + 
        settings.EDUCATION_WEIGHT + 
        settings.KEYWORDS_WEIGHT
    )
    
    if abs(weights_sum - 1.0) > 0.01:
        errors.append(f"Scoring weights must sum to 1.0, got {weights_sum}")
    
    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")
    
    return True