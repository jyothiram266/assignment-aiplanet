import pytest
from fastapi.testclient import TestClient
from main import app, select_model_backend

client = TestClient(app)

def test_healthz_endpoint():
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "canary_split" in data

def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "llm_gateway_requests_total" in response.text
    assert "llm_gateway_canary_weight" in response.text

def test_model_selection():
    backend_url, version = select_model_backend()
    assert version in ["v1", "v2"]
    assert "http://" in backend_url

def test_chat_completions_mock_fallback():
    payload = {
        "messages": [
            {"role": "user", "content": "What is the return policy?"}
        ]
    }
    response = client.post("/v1/chat/completions", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "choices" in data
    assert len(data["choices"]) > 0
    assert "message" in data["choices"][0]
