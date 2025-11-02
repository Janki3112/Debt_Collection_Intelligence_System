import os
from pathlib import Path
from dotenv import load_dotenv

# Get project root (repo folder) - go up from app/core/config.py
# app/core/config.py -> app/core -> app -> repo
project_root = Path(__file__).parent.parent.parent
env_path = project_root / '.env'

# Load environment variables from .env
load_dotenv(dotenv_path=env_path)

class Settings:
    PROJECT_NAME: str = "Debt Collection Intelligence System"
    DB_URL: str = os.getenv("DB_URL", "sqlite+aiosqlite:///./documents.db")
    STORAGE_PATH: str = os.getenv("STORAGE_PATH", "./storage")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    SQL_ECHO: bool = os.getenv("SQL_ECHO", "False").lower() == "true"
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "*")

settings = Settings()