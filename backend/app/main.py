import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.v1.router import api_router

# Configuración de logging para diagnóstico en macOS
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

app = FastAPI(
    title="GovAssist Core API",
    description="Backend asíncrono para simplificación de trámites federales (IHC + RPA + NLP)",
    version="1.0.0"
)

# Middleware CORS permisivo para la PWA (Next.js)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción se restringirá al dominio de Vercel
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Integración del enrutador principal
app.include_router(api_router, prefix="/api/v1")

@app.get("/health", tags=["Sistema"])
def health_check():
    """Endpoint de comprobación de estado para despliegues (Render/Koyeb)."""
    return {"status": "ok", "message": "GovAssist Core Backend operando en macOS Monterey"}
