import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_root_and_health():
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["system"] == "ORBIT"
    assert res.json()["falkordb_connected"] is True

    health_res = client.get("/health")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "healthy"

def test_graph_stats_endpoint():
    res = client.get("/api/graph/stats")
    assert res.status_code == 200
    data = res.json()
    assert data["connected"] is True
    assert data["total_nodes"] > 0

def test_graph_elements_endpoint():
    res = client.get("/api/graph/elements")
    assert res.status_code == 200
    data = res.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) > 0

def test_scenarios_endpoint():
    for scene_id in ["scene_1", "scene_2", "scene_3", "scene_4"]:
        res = client.get(f"/api/scenarios/{scene_id}")
        assert res.status_code == 200

def test_comparison_endpoint():
    res = client.get("/api/comparison")
    assert res.status_code == 200
    data = res.json()
    assert "comparison" in data
