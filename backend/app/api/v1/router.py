from fastapi import APIRouter
import importlib
import logging

logger = logging.getLogger("govassist-router")
api_router = APIRouter()

# Diccionario de módulos a cargar (módulo: (prefijo, etiqueta))
# Incluye los módulos de las Semanas 1, 2 y el nuevo de la Semana 4
ROUTE_MODULES = {
    "chat": ("/chat", "Chat Conversacional & RAG"),
    "rpa": ("/rpa", "Automatización RPA (Playwright)"),
    "telemetry": ("/telemetry", "Telemetría & Evaluación SUS")
}

# Carga dinámica y resiliente para evitar colapsos de Uvicorn en producción
for module_name, (prefix, tag) in ROUTE_MODULES.items():
    try:
        module = importlib.import_module(f"app.api.v1.endpoints.{module_name}")
        api_router.include_router(module.router, prefix=prefix, tags=[tag])
        logger.info(f"Router de FastAPI montado exitosamente: {prefix}")
    except ModuleNotFoundError:
        logger.warning(f"Módulo '{module_name}' no encontrado. Se omitirá en este despliegue para evitar caídas de servidor.")
    except AttributeError:
        logger.warning(f"El módulo '{module_name}' existe pero no expone un objeto 'router'.")
    except Exception as e:
        logger.error(f"Error inesperado al cargar el router '{module_name}': {str(e)}")
