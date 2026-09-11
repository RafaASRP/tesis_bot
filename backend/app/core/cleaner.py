import os
import time
import logging
from pathlib import Path
from typing import Optional
from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class EphemeralFileManager:
    """
    Gestor de purga y ciclo de vida efímero para documentos oficiales y archivos temporales.
    Garantiza el cumplimiento del principio de minimización de datos (LGPDPPSO).
    """

    def __init__(self, target_dir: Optional[Path] = None):
        self.target_dir = Path(target_dir or settings.DOWNLOADS_PATH)
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """Crea el directorio de descargas efímeras si no existe."""
        try:
            self.target_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Error al asegurar el directorio efímero {self.target_dir}: {e}")

    def purge_file(self, file_path: Path) -> bool:
        """
        Elimina de forma segura un archivo individual inmediatamente tras su entrega o error.
        """
        path = Path(file_path)
        try:
            if path.is_file() and path.exists():
                path.unlink(missing_ok=True)
                logger.info(f"Archivo efímero purgado exitosamente: {path.name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Fallo al purgar archivo efímero {path}: {e}")
            return False

    def purge_expired_files(self, max_age_seconds: int = 300) -> int:
        """
        Elimina todos los archivos del directorio de descargas cuya antigüedad
        supere el umbral establecido (por defecto 300 segundos = 5 minutos).
        Retorna la cantidad de archivos purgados.
        """
        if not self.target_dir.exists():
            return 0

        current_time = time.time()
        purged_count = 0

        try:
            for item in self.target_dir.iterdir():
                if item.is_file() and not item.name.startswith("."):
                    file_age = current_time - item.stat().st_mtime
                    if file_age >= max_age_seconds:
                        try:
                            item.unlink(missing_ok=True)
                            purged_count += 1
                            logger.info(f"Purga programada: archivo expirado eliminado -> {item.name}")
                        except Exception as file_err:
                            logger.error(f"Error al purgar archivo {item.name}: {file_err}")
        except Exception as dir_err:
            logger.error(f"Error al explorar directorio efímero durante purga: {dir_err}")

        return purged_count


# Instancia singleton para BackgroundTasks y servicios RPA
cleaner_manager = EphemeralFileManager()
