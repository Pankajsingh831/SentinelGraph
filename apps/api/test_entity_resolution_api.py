import httpx
import pytest

BASE_URL = "http://127.0.0.1:8000"
VALID_CASE_ID = "0adbb74e-2715-490e-9beb-b6b910466f4e"
NON_EXISTENT_CASE_ID = "00000000-0000-0000-0000-000000000000"


@pytest.fixture
def client():
    # Authenticate to get demo token
    login_resp = httpx.post(f"{BASE_URL}/api/v1/auth/login", json={"username": "admin", "password": "admin123"}, timeout=15.0)
    token = login_resp.json().get("token") if login_resp.status_code == 200 else None
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return httpx.Client(base_url=BASE_URL, headers=headers, timeout=30.0)


def test_1_valid_case_entity_resolution_returns_200(client):
    """1. Valid case entity-resolution endpoint returns 200 with complete schema."""
    resp = client.get(f"/api/v1/cases/{VALID_CASE_ID}/entity-resolution")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()

    assert data["case_id"] == VALID_CASE_ID
    assert "canonical_entity" in data
    assert "resolved_identifiers" in data
    assert "correlated_cases" in data
    assert data["resolution_strategy"] == "DETERMINISTIC_GRAPH_LINKING"
    assert data["confidence_model"] == "RULE_BASED_GROUND_TRUTH"
    assert len(data["summary"]) > 10


def test_2_canonical_entity_attributes(client):
    """2. Canonical entity returns correct customer metrics and identifiers."""
    resp = client.get(f"/api/v1/cases/{VALID_CASE_ID}/entity-resolution")
    assert resp.status_code == 200
    canonical = resp.json()["canonical_entity"]

    assert canonical["entity_type"] == "customer"
    assert len(canonical["canonical_id"]) == 36
    assert canonical["total_transactions"] >= 1
    assert canonical["total_cases"] >= 1
    assert canonical["correlated_devices_count"] >= 1
    assert canonical["correlated_instruments_count"] >= 1
    assert canonical["correlated_ips_count"] >= 1


def test_3_resolved_identifiers_structure(client):
    """3. Resolved identifiers contain deterministic confidence, methods, and shared counts."""
    resp = client.get(f"/api/v1/cases/{VALID_CASE_ID}/entity-resolution")
    assert resp.status_code == 200
    identifiers = resp.json()["resolved_identifiers"]
    assert len(identifiers) >= 3

    id_types = {item["identifier_type"] for item in identifiers}
    assert "transaction" in id_types or "device" in id_types or "payment_instrument" in id_types

    for item in identifiers:
        assert item["confidence"] == 1.0, "Must be honest deterministic confidence (1.0)"
        assert item["status"] in ("RESOLVED", "SUSPICIOUS_SHARED", "UNRESOLVED")
        assert item["shared_with_customers_count"] >= 1
        assert len(item["resolution_method"]) > 0


def test_4_correlated_cases_linkage(client):
    """4. Shows cross-case correlation for the same canonical entity."""
    resp = client.get(f"/api/v1/cases/{VALID_CASE_ID}/entity-resolution")
    assert resp.status_code == 200
    cases = resp.json()["correlated_cases"]
    assert len(cases) >= 1
    case_ids = [c["case_id"] for c in cases]
    assert VALID_CASE_ID in case_ids


def test_5_nonexistent_case_returns_404(client):
    """5. Nonexistent case returns 404."""
    resp = client.get(f"/api/v1/cases/{NON_EXISTENT_CASE_ID}/entity-resolution")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "CASE_NOT_FOUND"


def test_6_invalid_uuid_returns_422(client):
    """6. Invalid UUID format returns 422."""
    resp = client.get("/api/v1/cases/not-a-uuid/entity-resolution")
    assert resp.status_code == 422
