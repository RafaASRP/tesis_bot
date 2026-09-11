import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.rag.ingestion import ingestion_pipeline
from backend.app.services.rag.rag_service import rag_service
from backend.app.models.telemetry import SUSSubmissionRequest

client = TestClient(app)


def test_raw_documents_exist():
    """Valida la presencia y contenido de las 5 fichas normativas oficiales."""
    docs = ingestion_pipeline.load_raw_documents()
    assert len(docs) == 5, f"Se esperaban 5 fichas normativas, se obtuvieron {len(docs)}"
    procedures = {doc.metadata["procedure"] for doc in docs}
    expected = {"curp", "acta_nacimiento", "semanas_imss", "pasaporte", "cedula_profesional"}
    assert procedures == expected, f"Fichas normativas faltantes: {expected - procedures}"


def test_rag_semantic_retrieval():
    """Valida la recuperación semántica de contexto relevante por coseno."""
    query = "¿Cuánto cuesta tramitar el pasaporte con descuento de INAPAM?"
    context = rag_service.retrieve_context(query)
    assert len(context) > 0, "El servicio RAG no recuperó ningún nodo relevante."
    top_doc = context[0]
    assert "pasaporte" in top_doc["procedure"], f"Documento esperado: pasaporte. Obtenido: {top_doc['procedure']}"
    assert top_doc["score"] > 0.0, "La puntuación de similitud debe ser positiva."


def test_chat_query_endpoint():
    """Valida el endpoint conversacional accesible con medición de latencia L."""
    payload = {
        "message": "¿Qué costo tiene consultar mi CURP certificada?",
        "session_id": "test_session_automated",
        "is_pre_test": False
    }
    response = client.post("/api/v1/chat/query", json=payload)
    assert response.status_code == 200, f"Error en endpoint: {response.text}"
    data = response.json()
    assert "reply" in data and len(data["reply"]) > 0
    assert "latency_seconds" in data and data["latency_seconds"] >= 0.0
    assert "model_used" in data
    assert len(data["sources"]) > 0


def test_telemetry_task_and_sus_endpoints():
    """Valida el registro de métricas T, E, L, S y el cálculo exacto de la Escala SUS."""
    # 1. Telemetría de tarea
    task_payload = {
        "session_id": "test_user_01",
        "procedure_name": "curp",
        "is_pre_test": False,
        "task_time_seconds": 38.5,
        "user_errors_count": 0,
        "llm_latency_seconds": 0.42,
        "success": 1,
        "voice_used": True
    }
    task_res = client.post("/api/v1/telemetry/task", json=task_payload)
    assert task_res.status_code == 201
    assert task_res.json()["record_type"] == "task_performance"

    # 2. Evaluación SUS (caso positivo perfecto = 100.0)
    sus_payload = {
        "session_id": "test_user_01",
        "is_pre_test": False,
        "q1": 5, "q2": 1, "q3": 5, "q4": 1, "q5": 5,
        "q6": 1, "q7": 5, "q8": 1, "q9": 5, "q10": 1
    }
    sus_res = client.post("/api/v1/telemetry/sus", json=sus_payload)
    assert sus_res.status_code == 201
    assert sus_res.json()["sus_score"] == 100.0
