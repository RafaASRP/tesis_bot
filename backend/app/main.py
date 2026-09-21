from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.v1.router import api_router
from backend.app.core.cleaner import setup_cleanup_task

app = FastAPI(
    title="GovAssist Core API",
    description="Backend híbrido (NLP + RPA) para automatización de trámites (Adultos 50+)",
    version="1.0.0"
)

# Lista Blanca CORS: Entornos de desarrollo local y Dominio Real de Producción (Vercel)
origins = [
    "http://localhost:3000",
    "http://0.0.0.0:3000",
    "https://govassist-core.vercel.app",
    "https://govassist-core-cs25u7987-rafaasrps-projects.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Integración del router principal Pydantic v2
app.include_router(api_router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    # Inicializa el purgado en segundo plano de PDFs efímeros (LGPDPPSO)
    setup_cleanup_task()

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "GovAssist Core Backend Operational", "version": "1.0.0"}
