from fastapi import APIRouter
from backend.app.api.v1.endpoints import chat, telemetry

api_router = APIRouter()

# Registro de rutas modulares del monorepo
api_router.include_router(chat.router, prefix="/chat", tags=["Conversacional NLP"])
api_router.include_router(telemetry.router, prefix="/telemetry", tags=["Telemetría y Usabilidad SUS"])
