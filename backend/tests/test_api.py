"""
ResourceShift AI - Test Suite for FastAPI Backend Endpoints
------------------------------------------------------------
Tests health check, multi-resource telemetry queries, anomaly feeds,
and human-in-the-loop action approval/rejection endpoints.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.audit import reset_audit_store, get_audit_trail


@pytest.fixture(autouse=True)
def clean_audit_state():
    """Ensures clean audit state for each test run."""
    reset_audit_store()
    yield
    reset_audit_store()


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint_no_secrets(client: TestClient):
    """Verifies /api/health returns 200, correct metadata, and no credentials or keys."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ResourceShift AI"
    assert "electricity" in data["resources_supported"]
    assert "water" in data["resources_supported"]
    assert "fuel" in data["resources_supported"]

    # Security verification: Ensure no secret strings or environment variables leaked
    raw_text = res.text.lower()
    assert "key" not in raw_text or "api_key" not in raw_text
    assert "secret" not in raw_text
    assert "password" not in raw_text


def test_telemetry_endpoint_pagination_and_filtering(client: TestClient):
    """Tests /api/telemetry with resource filters, building filters, and pagination."""
    # All telemetry default
    res = client.get("/api/telemetry?limit=25")
    assert res.status_code == 200
    data = res.json()
    assert len(data["readings"]) == 25
    assert data["total"] == 672 * 3  # 2016 total readings

    # Filter water
    res_w = client.get("/api/telemetry?resource_type=water&limit=10")
    assert res_w.status_code == 200
    data_w = res_w.json()
    assert len(data_w["readings"]) == 10
    assert all(r["resource_type"] == "water" for r in data_w["readings"])
    assert data_w["total"] == 672

    # Filter fuel
    res_f = client.get("/api/telemetry?resource_type=fuel&limit=10")
    assert res_f.status_code == 200
    data_f = res_f.json()
    assert all(r["resource_type"] == "fuel" for r in data_f["readings"])

    # Invalid resource type returns 422
    res_bad = client.get("/api/telemetry?resource_type=plutonium")
    assert res_bad.status_code == 422


def test_anomalies_endpoint_filtering(client: TestClient):
    """Tests /api/anomalies endpoint with resource and severity filters."""
    # All anomalies
    res = client.get("/api/anomalies")
    assert res.status_code == 200
    data = res.json()
    assert data["total_anomalies"] == 50 + 28 + 28  # 106 total anomalies

    # Filter electricity
    res_elec = client.get("/api/anomalies?resource_type=electricity")
    assert res_elec.status_code == 200
    assert res_elec.json()["total_anomalies"] == 50

    # Filter severity
    res_crit = client.get("/api/anomalies?severity=critical")
    assert res_crit.status_code == 200
    assert all(a["severity"] == "critical" for a in res_crit.json()["anomalies"])

    # Invalid severity returns 422
    res_bad = client.get("/api/anomalies?severity=catastrophic")
    assert res_bad.status_code == 422


def test_actions_approve_and_audit_trail(client: TestClient):
    """Tests /api/actions/approve and verifies audit log entry creation."""
    payload = {
        "proposal_id": "PROP-ELEC-001",
        "approved_by": "swayam_director",
        "notes": "Approved HVAC setback on 3rd floor. Ticket #1043.",
    }
    res = client.post("/api/actions/approve", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "approved"
    assert data["proposal_id"] == "PROP-ELEC-001"
    assert data["actor"] == "swayam_director"
    assert data["no_actuation_guarantee"] is True
    assert data["audit_id"].startswith("AUDIT-")

    # Verify audit store records the event
    trail = get_audit_trail(proposal_id="PROP-ELEC-001")
    assert len(trail) == 1
    assert trail[0]["decision"] == "approved"
    assert trail[0]["actor"] == "swayam_director"


def test_actions_reject_and_audit_trail(client: TestClient):
    """Tests /api/actions/reject and verifies audit record with rejection reason."""
    payload = {
        "proposal_id": "PROP-WATE-002",
        "rejected_by": "swayam_director",
        "reason": "Late night lab cleaning scheduled tonight; water is legitimate.",
    }
    res = client.post("/api/actions/reject", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "rejected"
    assert data["proposal_id"] == "PROP-WATE-002"
    assert data["actor"] == "swayam_director"
    assert "Late night lab cleaning" in data["notes_or_reason"]


def test_actions_empty_body_rejection(client: TestClient):
    """Verifies that invalid or empty bodies are rejected with 422 Unprocessable Entity."""
    res = client.post("/api/actions/approve", json={})
    assert res.status_code == 422

    res_rej = client.post("/api/actions/reject", json={})
    assert res_rej.status_code == 422
