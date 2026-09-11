from pathlib import Path
from typing import List, Union
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # Entorno y metadatos
    PROJECT_NAME: str = "GovAssist Core"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Inferencia LLM (Groq LPU)
    GROQ_API_KEY: str = Field(default="mock_groq_key")
    GROQ_MODEL: str = "llama3-70b-8192"

    # Base vectorial (Pinecone)
    PINECONE_API_KEY: str = Field(default="mock_pinecone_key")
    PINECONE_ENVIRONMENT: str = "us-east-1"
    PINECONE_INDEX_NAME: str = "govassist-docs"

    # Base de datos y métricas (Supabase)
    SUPABASE_URL: str = Field(default="https://mock.supabase.co")
    SUPABASE_KEY: str = Field(default="mock_supabase_key")

    # Seguridad y cifrado simétrico AES-256 (Fernet)
    SECRET_ENCRYPTION_KEY: str = Field(default="")

    # Rutas físicas del sistema
    DOWNLOADS_PATH: Path = Field(default=Path("backend/data/downloads"))
    RAW_DOCS_PATH: Path = Field(default=Path("backend/data/raw_docs"))

    # Configuración de CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]


settings = Settings()
