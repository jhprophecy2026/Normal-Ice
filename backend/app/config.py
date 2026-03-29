import os
from pathlib import Path
from dotenv import load_dotenv

# Always load from backend/.env regardless of where the process is started from
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env", override=True)

class Settings:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8000))
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")

    # Gemini Configuration
    GEMINI_MODEL: str = "models/gemini-2.5-flash"
    GEMINI_TEMPERATURE: float = 0.1
    GEMINI_MAX_TOKENS: int = 8192

    # File Upload Configuration
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: set = {".pdf"}

    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")  # use service_role key for backend

    # Email (Resend) — leave RESEND_API_KEY blank to disable (emails logged instead)
    RESEND_API_KEY:    str = os.getenv("RESEND_API_KEY", "")
    FROM_EMAIL:        str = os.getenv("FROM_EMAIL", "onboarding@resend.dev")
    DEFAULT_TPA_EMAIL: str = os.getenv("DEFAULT_TPA_EMAIL", "tpa-claims@example.com")

settings = Settings()
