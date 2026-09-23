import uvicorn
import logging
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger("govassist-core-runner")

def main():
    # Extracción segura con getattr para evitar caídas si hay lag en la propagación de variables
    env_mode = getattr(settings, "ENVIRONMENT", "production")
    logger.info(f"Iniciando GovAssist Core (Backend) en entorno: {env_mode}")
    logger.info("Motor ASGI: Uvicorn 0.30.1 | Framework: FastAPI 0.111.0")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=10000,
        reload=False,  # Desactivado obligatoriamente para producción (evita colapsos de memoria)
        workers=1,     # Límite a 1 worker para estabilizar la instancia
        proxy_headers=True,
        forwarded_allow_ips="*"
    )

if __name__ == "__main__":
    main()
