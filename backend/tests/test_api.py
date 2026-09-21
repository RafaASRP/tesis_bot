import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health_check():
    """Valida que el servidor ASGI responda correctamente en el endpoint de salud."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "GovAssist Core Backend" in data.get("message", "GovAssist Core Backend operando en macOS Monterey")

def test_chat_query_nlp_intent():
    """Valida la recepción de mensajes en el chat y la detección heurística de la intención CURP."""
    response = client.post(
        "/api/v1/chat/query",
        json={
            "messages": [
                {"role": "user", "content": "Hola, necesito consultar mi CURP por favor"}
            ],
            "session_id": "test_session_integration_01"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert len(data["reply"]) > 0
    assert data["detected_intent"] == "curp"
    assert isinstance(data["is_fallback"], bool)
