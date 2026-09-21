from fastapi import APIRouter
from backend.app.api.v1.endpoints import chat

api_router = APIRouter()

# Registro de rutas modulares
api_router.include_router(chat.router, prefix="/chat", tags=["Conversacional NLP"])
# Aquí conectaremos los endpoints RPA y de Telemetría en el futuro
