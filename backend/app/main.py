import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.cleaner import cleaner_manager
from backend.app.api.v1.router import api_router

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("govassist.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestión del ciclo de vida del servidor.
    Asegura los directorios efímeros al arrancar y purga archivos al detenerse.
    """
    logger.info(f"Iniciando {settings.PROJECT_NAME} ({settings.ENVIRONMENT})")
    settings.DOWNLOADS_PATH.mkdir(parents=True, exist_ok=True)
    settings.RAW_DOCS_PATH.mkdir(parents=True, exist_ok=True)
    yield
    logger.info("Cerrando servicio. Ejecutando purga final de archivos temporales...")
    cleaner_manager.purge_expired_files(max_age_seconds=0)


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API accesible y motor conversacional/RPA para la simplificación de trámites federales (gob.mx).",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# Configuración estricta de CORS para Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montaje de la versión 1 de la API
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Raíz"])
async def root():
    return {
        "sistema": settings.PROJECT_NAME,
        "estado": "activo",
        "documentacion": f"{settings.API_V1_STR}/docs"
    }
