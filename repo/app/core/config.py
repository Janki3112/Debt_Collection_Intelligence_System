import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../.env'))

class Settings:
    PROJECT_NAME: str = "Debt Collection Intelligence System"
    DB_URL: str = os.getenv("DB_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_developer_db")
    STORAGE_PATH: str = os.getenv("STORAGE_PATH", "./storage")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    SQL_ECHO: bool = os.getenv("SQL_ECHO", "False").lower() == "true"
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "*")

settings = Settings()
