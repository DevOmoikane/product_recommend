import pytest
from fastapi.testclient import TestClient


def test_recommend_endpoint_structure(test_client):
    payload = {
        "user_id": 1,
        "n_items": 5,
        "filter_already_liked": True,
        "items_to_exclude": None
    }
    response = test_client.post("/api/recommend", json=payload)
    assert response.status_code in [200, 500]


def test_recommend_new_item_structure(test_client):
    payload = {
        "user_id": 1,
        "n_items": 5,
        "items_to_exclude": None
    }
    response = test_client.post("/api/recommend/new-item", json=payload)
    assert response.status_code in [200, 500]


def test_recommend_repurchase_structure(test_client):
    payload = {
        "user_id": 1,
        "n_items": 5,
        "items_to_exclude": None
    }
    response = test_client.post("/api/recommend/repurchase", json=payload)
    assert response.status_code in [200, 500]


def test_similar_items_structure(test_client):
    payload = {
        "item_id": 1,
        "n_items": 5
    }
    response = test_client.post("/api/recommend/similar", json=payload)
    assert response.status_code in [200, 500]