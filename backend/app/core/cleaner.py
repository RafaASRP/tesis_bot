import os
import shutil
import logging
from pathlib import Path
from backend.app.core.config import settings

logger = logging.getLogger(__name__)


def purge_ephemeral_storage():
    """
    Elimina archivos PDF descargados y limpia perfiles temporales de Playwright
    para garantizar el cumplimiento de la LGPDPPSO y evitar saturación de I/O.
    """
    downloads_path = Path(settings.DOWNLOADS_PATH)
    if downloads_path.exists():
        for file in downloads_path.glob("*.pdf"):
            try:
                file.unlink()
                logger.info(f"Archivo efímero eliminado: {file.name}")
            except Exception as e:
                logger.warning(f"No se pudo eliminar {file.name}: {e}")

    # Limpieza de perfiles residuales en /tmp
    tmp_path = Path("/tmp")
    for item in tmp_path.glob("playwright_*"):
        try:
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)
        except Exception:
            pass


def reset_environment_caches():
    """Limpia variables y archivos temporales del sistema."""
    os.system("pkill -f 'Chromium|Google Chrome' 2>/dev/null || true")
    purge_ephemeral_storage()
