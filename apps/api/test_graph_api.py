import httpx
import pytest

BASE_URL = "http://127.0.0.1:8000"
CUSTOMER_ID = "5c5001a1-887e-45e7-8ae8-f1c53fa808b0"

@pytest.fixture
def client():
    return httpx.Client(base_url=BASE_URL, timeout=30.0)

def test_1_valid_customer_graph_returns_nodes(client):
    """1. Valid customer graph returns real nodes."""
    resp = client.get(f"/api/v1/graph/entity/customer/{CUSTOMER_ID}")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert len(data["nodes"]) >= 5
    node_ids = [n["id"] for n in data["nodes"]]
    assert CUSTOMER_ID in node_ids
    node_types = {n["type"] for n in data["nodes"]}
    assert "Customer" in node_types

def test_2_valid_customer_graph_returns_edges(client):
    """2. Valid customer graph returns real edges."""
    resp = client.get(f"/api/v1/graph/entity/customer/{CUSTOMER_ID}")
    assert resp.status_code == 200
    data = resp.json()
    assert "edges" in data
    assert len(data["edges"]) >= 4
    edge_types = {e["type"] for e in data["edges"]}
    assert "MADE" in edge_types or "USES" in edge_types

def test_3_valid_neighbors_returns_data(client):
    """3. Valid neighbors returns neighbor data."""
    resp = client.get(f"/api/v1/graph/entity/customer/{CUSTOMER_ID}/neighbors?depth=1&limit=50")
    assert resp.status_code == 200
    data = resp.json()
    assert "neighbors" in data
    assert len(data["neighbors"]) >= 4
    assert data["depth"] == 1
    assert data["limit"] == 50

def test_4_unsupported_entity_type_rejected(client):
    """4. Unsupported entity type rejected with 400."""
    resp = client.get(f"/api/v1/graph/entity/unsupported_type/{CUSTOMER_ID}")
    assert resp.status_code == 400
    assert "Unsupported entity type" in resp.json()["detail"]

def test_5_invalid_entity_id_handled_correctly(client):
    """5. Invalid entity ID handled with 400."""
    resp = client.get("/api/v1/graph/entity/customer/invalid-uuid-format")
    assert resp.status_code == 400
    assert "Invalid entity ID" in resp.json()["detail"]

def test_6_nonexistent_entity_handled_correctly(client):
    """6. Nonexistent entity returns empty graph without crashing."""
    resp = client.get("/api/v1/graph/entity/customer/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 200
    data = resp.json()
    assert data["nodes"] == []
    assert data["edges"] == []
    assert data["degraded"] is False

def test_7_depth_and_limit_behavior(client):
    """7. Depth and limit parameters are respected and bounded."""
    r1 = client.get(f"/api/v1/graph/entity/customer/{CUSTOMER_ID}/neighbors?depth=1&limit=50")
    r2 = client.get(f"/api/v1/graph/entity/customer/{CUSTOMER_ID}/neighbors?depth=2&limit=50")
    assert r1.status_code == 200 and r2.status_code == 200
    d1 = r1.json()
    d2 = r2.json()
    assert len(d2["neighbors"]) >= len(d1["neighbors"])
    assert len(d2["edges"]) >= len(d1["edges"])

    r_limit = client.get(f"/api/v1/graph/entity/customer/{CUSTOMER_ID}/neighbors?depth=1&limit=2")
    assert r_limit.status_code == 200
    assert r_limit.json()["limit"] == 2

def test_8_no_duplicate_nodes_or_edges(client):
    """8. Ensure no duplicate nodes or edges are returned."""
    resp = client.get(f"/api/v1/graph/entity/customer/{CUSTOMER_ID}")
    assert resp.status_code == 200
    data = resp.json()
    node_ids = [n["id"] for n in data["nodes"]]
    assert len(node_ids) == len(set(node_ids)), "Duplicate nodes found!"
    edges = [(e["source"], e["target"], e["type"]) for e in data["edges"]]
    assert len(edges) == len(set(edges)), "Duplicate edges found!"
