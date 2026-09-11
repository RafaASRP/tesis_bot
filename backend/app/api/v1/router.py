from fastapi import APIRouter
from backend.app.core.config import settings

api_router = APIRouter()


@api_router.get("/health", tags=["Salud del Sistema"])
async def health_check():
    """
    Endpoint base de diagnóstico y telemetría de vida del servicio.
    Valida el estado de operación de GovAssist Core.
    """
    return {
        "status": "online",
        "project": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0"
    }


# Los routers específicos se montarán conforme completemos sus módulos:
# from backend.app.api.v1.endpoints import chat, rpa, telemetry
# api_router.include_router(chat.router, prefix="/chat", tags=["Cerebro Conversacional"])
# api_router.include_router(rpa.router, prefix="/rpa", tags=["Automatización RPA"])
# api_router.include_router(telemetry.router, prefix="/telemetry", tags=["Telemetría Cuantitativa"])
