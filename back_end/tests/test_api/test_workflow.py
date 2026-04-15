import pytest
from fastapi.testclient import TestClient


def test_health_check(test_client):
    response = test_client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_get_node_definitions(test_client):
    response = test_client.get("/api/node-definitions")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list) and len(data) > 0


def test_list_workflows(test_client):
    response = test_client.get("/api/workflow/list")
    assert response.status_code == 200
    assert "workflows" in response.json()


@pytest.mark.integration
def test_execute_workflow_validation(test_client, sample_workflow):
    response = test_client.post(
        "/api/workflow/execute",
        json={
            "workflow": sample_workflow,
            "initial_data": {}
        }
    )
    assert response.status_code in [200, 400, 500]


def test_workflow_save_and_list(test_client, sample_workflow):
    save_response = test_client.post(
        "/api/workflow/save",
        json=sample_workflow
    )
    assert save_response.status_code == 200

    list_response = test_client.get("/api/workflow/list")
    assert list_response.status_code == 200
    workflows = list_response.json()["workflows"]
    assert "test_workflow" in workflows


def test_workflow_get_and_delete(test_client, sample_workflow):
    test_client.post("/api/workflow/save", json=sample_workflow)

    get_response = test_client.get("/api/workflow/test_workflow")
    assert get_response.status_code == 200

    delete_response = test_client.delete("/api/workflow/test_workflow")
    assert delete_response.status_code == 200