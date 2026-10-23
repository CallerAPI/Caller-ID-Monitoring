from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path

class Settings(BaseSettings):
    PROJECT_NAME: str = "Caller ID Monitor"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "sqlite:///./caller_id.db"
    
    # API Keys
    CALLER_API_URL: str = "https://callerapi.com"
    
    # Security
    SESSION_SECRET: str = ""
    
    # Templates
    TEMPLATES_DIR: Path = Path(__file__).parent.parent / "templates"
    STATIC_DIR: Path = Path(__file__).parent.parent.parent / "static"

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings() 
