from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    """
    Validación estricta de variables de entorno mediante Pydantic v2.
    El servidor ASGI abortará el arranque si falta alguna de estas credenciales.
    """
    ENVIRONMENT: str = Field(default="production")
    DEBUG: bool = Field(default=False)
    API_V1_STR: str = Field(default="/api/v1")

    # Inferencia Groq LPU (Lenguaje Ciudadano)
    GROQ_API_KEY: str = Field(..., description="Token de acceso a Groq Cloud")
    GROQ_MODEL: str = Field(default="llama3-70b-8192")

    # Vector Store Pinecone (Cerebro RAG)
    PINECONE_API_KEY: str = Field(..., description="Token de Pinecone Serverless")
    PINECONE_ENVIRONMENT: str = Field(default="us-east-1")
    PINECONE_INDEX_NAME: str = Field(default="govassist-docs")

    # Base de datos y Telemetría cuantitativa (T, E, L, S)
    SUPABASE_URL: str = Field(..., description="URL HTTPS del proyecto Supabase")
    SUPABASE_KEY: str = Field(..., description="Clave anon public de Supabase")

    # Criptografía simétrica (LGPDPPSO - Privacidad desde el Diseño)
    SECRET_ENCRYPTION_KEY: str = Field(..., description="Llave Fernet AES-256")

    # Rutas efímeras del sistema
    DOWNLOADS_PATH: str = Field(default="backend/data/downloads")
    RAW_DOCS_PATH: str = Field(default="backend/data/raw_docs")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
