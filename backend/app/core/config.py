import os
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings(BaseModel):
    PROJECT_NAME: str = "DevSentinel"
    API_PREFIX: str = "/api"
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/devsentinel.db")
    SANDBOX_TIMEOUT_SECONDS: int = int(os.getenv("SANDBOX_TIMEOUT_SECONDS", "30"))
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", os.getenv("GEMINI_API_KEY", "")))
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "auto") # "openai", "gemini", "demo", "auto"
    ALLOWED_REPO_ROOTS: list[str] = [
        str(BASE_DIR.parent),
        str(BASE_DIR / "sample_repos"),
        "sample_repos"
    ]
    CORS_ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

settings = Settings()
