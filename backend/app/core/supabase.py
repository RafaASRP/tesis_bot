import logging
from typing import Optional
from supabase import create_client, Client
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class SupabaseManager:
    """
    Gestor singleton para la conexión con Supabase (PostgreSQL).
    Incluye un mecanismo de contingencia si las credenciales no están presentes,
    permitiendo el almacenamiento local en memoria durante el desarrollo offline.
    """
    _instance: Optional[Client] = None

    @classmethod
    def get_client(cls) -> Optional[Client]:
        if cls._instance is None:
            if settings.SUPABASE_URL and settings.SUPABASE_KEY:
                try:
                    cls._instance = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                    logger.info("Conexión exitosa con Supabase establecida.")
                except Exception as e:
                    logger.error(f"Error al inicializar cliente Supabase: {str(e)}. Activando modo offline.")
            else:
                logger.warning("SUPABASE_URL o SUPABASE_KEY no definidos. El sistema operará sin persistencia en nube.")
        return cls._instance

supabase = SupabaseManager.get_client()
