import pytest
from fastapi.testclient import TestClient
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


@pytest.fixture(scope="session")
def test_config():
    return {
        "database": {
            "uri": "postgresql://postgres:arkus123@172.17.0.1:5432/testdata"
        },
        "csv": {
            "interactions_path": "./data/interactions.csv",
            "items_path": "./data/products.csv",
            "users_path": "./data/clients.csv"
        },
        "column_mapping": {
            "user_id": "client_id",
            "item_id": "product_id",
            "rating": "quantity"
        },
        "models": {
            "default": "als",
            "als": {
                "factors": 50,
                "regularization": 0.01,
                "iterations": 20
            }
        },
        "recommendations": {
            "default_n_items": 10,
            "filter_items": []
        },
        "persistence": {
            "models_dir": "./models",
            "data_dir": "./data",
            "default_model": "./models/model.pkl",
            "repurchase_model": "./models/model_repurchase.pkl"
        },
        "workflows": {
            "storage_path": "./workflows/",
            "execution": {
                "stop_grace_period_seconds": 30,
                "force_kill_after_seconds": 60
            }
        }
    }


@pytest.fixture
def test_client():
    from back_end.api.main import app
    return TestClient(app)


@pytest.fixture
def sample_workflow():
    return {
        "name": "test_workflow",
        "description": "Test workflow",
        "nodes": [
            {
                "id": "node1",
                "type": "StringNode",
                "fields": {"value": "test"},
                "processing_function": "output"
            }
        ],
        "connections": []
    }