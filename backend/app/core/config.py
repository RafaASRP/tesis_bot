import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "GovAssist Core"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Credenciales opcionales con respaldo local para desarrollo offline
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    DOWNLOADS_PATH: str = os.path.join(os.path.dirname(__file__), "../../data/downloads")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
