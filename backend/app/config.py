from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path


class Settings(BaseSettings):
    # Application settings
    app_name: str = "Course-Content-to-Study-Guide Generator"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # Database settings
    database_url: str = "postgresql://user:password@localhost/course_study_guide"
    redis_url: str = "redis://localhost:6379"
    
    # API settings
    api_v1_prefix: str = "/api/v1"
    secret_key: str = "your-secret-key-here"  # In production, use a strong secret
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # File upload settings
    max_file_size: int = 50 * 1024 * 1024  # 50MB in bytes
    allowed_file_types: list = [
        "application/pdf", 
        "application/msword", 
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "image/jpeg", 
        "image/png",
        "text/plain",
        "text/markdown"
    ]
    upload_directory: str = "./uploads"
    
    # LLM settings
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    default_llm_model: str = "claude-3-sonnet-20240229"  # Anthropic Claude
    
    # Processing settings
    processing_timeout: int = 300  # 5 minutes in seconds
    max_concurrent_processes: int = 5
    
    # Storage settings
    s3_bucket_name: Optional[str] = None
    s3_region: str = "us-east-1"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()

# Ensure upload directory exists
upload_path = Path(settings.upload_directory)
upload_path.mkdir(parents=True, exist_ok=True)