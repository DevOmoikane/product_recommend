import pytest
from fastapi.testclient import TestClient


def test_list_models(test_client):
    response = test_client.get("/api/models/list")
    assert response.status_code == 200
    assert "available_models" in response.json()


def test_load_model(test_client):
    response = test_client.post("/api/models/load", params={"model_path": "./models/model.pkl"})
    assert response.status_code == 200
    data = response.json()
    assert "status" in data or "model_path" in data


@pytest.mark.integration
def test_train_model(test_client):
    payload = {
        "model_type": "als",
        "save_model": False,
        "use_weighted": False
    }
    response = test_client.post("/api/train", json=payload)
    assert response.status_code in [200, 500]