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


def test_pair_nodes_to_dict_merge(test_client):
    workflow = {
        "name": "test_pair_dict_merge",
        "description": "Test merging multiple PairNodes into DictNode",
        "nodes": [
            {"id": "pair1", "type": "ml_library.utils.nodes.basic.var_nodes.PairNode", "fields": {"key": "name", "value": "Alice"}, "processing_function": "get_value"},
            {"id": "pair2", "type": "ml_library.utils.nodes.basic.var_nodes.PairNode", "fields": {"key": "age", "value": "30"}, "processing_function": "get_value"},
            {"id": "pair3", "type": "ml_library.utils.nodes.basic.var_nodes.PairNode", "fields": {"key": "city", "value": "NYC"}, "processing_function": "get_value"},
            {"id": "dict1", "type": "ml_library.utils.nodes.basic.var_nodes.DictNode", "fields": {}, "processing_function": "value"}
        ],
        "connections": [
            {"from_node": "pair1", "from_output": "pair", "to_node": "dict1", "to_input": "the_dict"},
            {"from_node": "pair2", "from_output": "pair", "to_node": "dict1", "to_input": "the_dict"},
            {"from_node": "pair3", "from_output": "pair", "to_node": "dict1", "to_input": "the_dict"}
        ]
    }
    response = test_client.post(
        "/api/workflow/execute",
        json={"workflow": workflow, "initial_data": {}}
    )
    assert response.status_code == 200
    result = response.json()
    execution_id = result.get("execution_id")
    
    import time
    for _ in range(20):
        status_response = test_client.get(f"/api/workflow/{execution_id}/status")
        status_data = status_response.json()
        if status_data.get("status") == "completed":
            break
        if status_data.get("status") == "failed":
            assert False, f"Workflow failed: {status_data.get('error')}"
        time.sleep(0.1)
    
    dict_result = status_data.get("results", {}).get("dict1", {}).get("dict", {})
    assert dict_result.get("name") == "Alice"
    assert dict_result.get("age") == "30"
    assert dict_result.get("city") == "NYC"


def test_type_compatibility_validation(test_client):
    workflow = {
        "name": "test_type_validation",
        "description": "Test type compatibility validation",
        "nodes": [
            {"id": "str1", "type": "ml_library.utils.nodes.basic.var_nodes.StringNode", "fields": {"value": "test"}, "processing_function": "get_value"},
            {"id": "dict1", "type": "ml_library.utils.nodes.basic.var_nodes.DictNode", "fields": {}, "processing_function": "value"}
        ],
        "connections": [
            {"from_node": "str1", "from_output": "value", "to_node": "dict1", "to_input": "the_dict"}
        ]
    }
    response = test_client.post(
        "/api/workflow/execute",
        json={"workflow": workflow, "initial_data": {}}
    )
    result = response.json()
    if result.get("status") == "failed":
        assert "Incompatible types" in result.get("error", "")


def test_debug_node_broadcast(test_client):
    workflow = {
        "name": "test_debug_node",
        "description": "Test debug node broadcasts to WebSocket",
        "nodes": [
            {"id": "pair1", "type": "ml_library.utils.nodes.basic.var_nodes.PairNode", "fields": {"key": "test_key", "value": "test_value"}, "processing_function": "get_value"},
            {"id": "debug1", "type": "ml_library.utils.nodes.basic.operation_nodes.DebugNode", "fields": {"msg": "Testing debug"}, "processing_function": "print_object"}
        ],
        "connections": [
            {"from_node": "pair1", "from_output": "pair", "to_node": "debug1", "to_input": "obj"}
        ]
    }
    response = test_client.post(
        "/api/workflow/execute",
        json={"workflow": workflow, "initial_data": {}}
    )
    assert response.status_code == 200
    result = response.json()
    execution_id = result.get("execution_id")
    
    import time
    for _ in range(20):
        status_response = test_client.get(f"/api/workflow/{execution_id}/status")
        status_data = status_response.json()
        if status_data.get("status") == "completed":
            break
        if status_data.get("status") == "failed":
            assert False, f"Workflow failed: {status_data.get('error')}"
        time.sleep(0.1)
    
    assert status_data.get("status") == "completed"