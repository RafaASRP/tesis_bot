import logging
from typing import Any, Dict, List, Optional
from supabase import create_client, Client
from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class SupabaseManager:
    """
    Cliente singleton para gestión de persistencia analítica y telemetría cuantitativa.
    Integra modo de contingencia local/offline para desarrollo y pruebas sin conexión.
    """

    def __init__(self):
        self._client: Optional[Client] = None
        self._offline_mode: bool = False
        self._offline_store: Dict[str, List[Dict[str, Any]]] = {
            "telemetry_metrics": [],
            "sus_responses": [],
            "procedure_logs": []
        }
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Inicializa la conexión oficial o activa el modo contingencia."""
        is_mock = "mock" in settings.SUPABASE_URL or "tu-proyecto" in settings.SUPABASE_URL
        if is_mock or not settings.SUPABASE_KEY:
            logger.warning("Supabase no configurado con credenciales válidas. Activando modo contingencia local.")
            self._offline_mode = True
            return

        try:
            self._client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            self._offline_mode = False
            logger.info("Conexión con Supabase establecida exitosamente.")
        except Exception as e:
            logger.error(f"Fallo al conectar con Supabase ({e}). Conmutando a modo contingencia local.")
            self._offline_mode = True

    @property
    def is_offline(self) -> bool:
        """Indica si el sistema opera en almacenamiento local en memoria."""
        return self._offline_mode

    def insert_record(self, table: str, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inserta un registro en la tabla especificada. Si la API remota
        falla o está en modo local, se guarda en el búfer en memoria.
        """
        if self._offline_mode or not self._client:
            if table not in self._offline_store:
                self._offline_store[table] = []
            self._offline_store[table].append(record)
            logger.debug(f"[Offline] Registro almacenado en búfer local para tabla '{table}'.")
            return {"status": "offline_saved", "data": record}

        try:
            response = self._client.table(table).insert(record).execute()
            return {"status": "success", "data": response.data}
        except Exception as err:
            logger.error(f"Error al escribir en Supabase ({table}): {err}. Guardando en búfer de contingencia.")
            if table not in self._offline_store:
                self._offline_store[table] = []
            self._offline_store[table].append(record)
            return {"status": "fallback_saved", "data": record}

    def fetch_offline_records(self, table: str) -> List[Dict[str, Any]]:
        """Recupera los datos en memoria cuando se opera en contingencia."""
        return self._offline_store.get(table, [])


# Singleton global de acceso a base de datos
supabase_manager = SupabaseManager()
