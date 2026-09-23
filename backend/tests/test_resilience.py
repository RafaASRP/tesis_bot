import time
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.llm.groq_client import nlp_engine

client = TestClient(app)

def test_heuristic_fallback_activation():
    """
    Valida que el sistema active el fallback heurístico local
    ante una caída de la API LLM en la nube, garantizando la 
    atención ininterrumpida (tolerancia a fallos 3G/4G).
    """
    # 1. Forzamos la desconexión simulada del cliente Groq (Caída de red)
    original_client = nlp_engine.client
    nlp_engine.client = None

    print("\n>> Iniciando prueba de resiliencia: Simulando desconexión de red 3G/4G...")
    start_time = time.time()
    
    # 2. Invocamos el endpoint de chat
    response = client.post(
        "/api/v1/chat/query",
        json={
            "messages": [{"role": "user", "content": "Quiero descargar mi curp pero mi internet esta lento"}],
            "session_id": "resilience_test_3g"
        }
    )
    latency = time.time() - start_time

    # 3. Restauramos el cliente para no afectar el estado global del backend
    nlp_engine.client = original_client

    assert response.status_code == 200
    data = response.json()
    
    # 4. Aserciones estrictas de arquitectura
    assert data["is_fallback"] is True, "El sistema no activó la bandera de fallback local."
    assert data["detected_intent"] == "curp", "Fallo en la extracción de intención heurística offline."
    assert latency < 1.0, f"Latencia inaceptable para el fallback local: {latency}s"
    
    print(f">> [RESILIENCIA APROBADA] Fallback heurístico activado exitosamente en {latency:.3f} segundos.")
    print(f">> Respuesta generada offline: '{data['reply']}'\n")

if __name__ == "__main__":
    test_heuristic_fallback_activation()
