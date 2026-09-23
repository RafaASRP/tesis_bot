import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("govassist_launcher")

if __name__ == "__main__":
    logger.info(">> Iniciando GovAssist Core - Modo Piloto (Expuesto en red local: 0.0.0.0:8000)")
    logger.info(">> Los dispositivos móviles en la misma red WiFi podrán conectarse a la IP de esta Mac.")
    
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        workers=1,
        log_level="info"
    )
