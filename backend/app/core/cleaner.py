import os
import logging
import asyncio
from pathlib import Path
from app.core.config import settings

logger = logging.getLogger("govassist-cleaner")

async def _periodic_cleanup() -> None:
    """
    Ciclo efímero de purga en segundo plano para cumplir con la privacidad 
    desde el diseño (LGPDPPSO).
    """
    while True:
        try:
            downloads_dir = Path(settings.DOWNLOADS_PATH)
            if downloads_dir.exists():
                for file_path in downloads_dir.glob("*.pdf"):
                    if file_path.is_file():
                        os.remove(file_path)
                        logger.info(f"Purga efímera ejecutada de forma segura (LGPDPPSO): {file_path.name}")
        except Exception as e:
            logger.error(f"Error en tarea de purga estructurada: {e}")
        
        # Ejecutar barrido asíncrono cada 300 segundos (5 minutos) sin bloquear el hilo principal
        await asyncio.sleep(300)

def setup_cleanup_task() -> None:
    """
    Inicializa la tarea asíncrona de limpieza de documentos temporales 
    dentro del event loop principal de FastAPI.
    """
    logger.info("Activando protocolo asíncrono de purga de documentos temporales (LGPDPPSO)...")
    asyncio.create_task(_periodic_cleanup())
