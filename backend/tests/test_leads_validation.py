"""Request-validation tests for the lead API that never touch a real database.

These rely on FastAPI validating the Pydantic request body before the
endpoint function body runs -- so a malformed request never reaches the
database layer, regardless of whether the referenced lead exists. The `db`
dependency is overridden with a MagicMock (see `mock_client` in conftest.py)
purely so these tests have zero dependency on Postgres being reachable.

Tests that need the endpoint body to actually execute (persistence,
pagination, 404-on-missing-row lookups, etc.) belong in test_leads.py
instead, which requires a real, isolated TEST_DATABASE_URL.
"""

import uuid


def test_create_lead_missing_company_name(mock_client, lead_payload):
    payload = {**lead_payload}
    del payload["company_name"]

    response = mock_client.post("/api/v1/leads", json=payload)

    assert response.status_code == 422


def test_create_lead_blank_company_name(mock_client, lead_payload):
    payload = {**lead_payload, "company_name": "   "}

    response = mock_client.post("/api/v1/leads", json=payload)

    assert response.status_code == 422


def test_create_lead_invalid_email(mock_client, lead_payload):
    payload = {**lead_payload, "contact_email": "not-an-email"}

    response = mock_client.post("/api/v1/leads", json=payload)

    assert response.status_code == 422


def test_create_lead_invalid_website(mock_client, lead_payload):
    payload = {**lead_payload, "website": "not-a-url"}

    response = mock_client.post("/api/v1/leads", json=payload)

    assert response.status_code == 422


def test_create_lead_invalid_status(mock_client, lead_payload):
    payload = {**lead_payload, "status": "not-a-real-status"}

    response = mock_client.post("/api/v1/leads", json=payload)

    assert response.status_code == 422


def test_update_lead_rejects_explicit_null_company_name(mock_client):
    # No real lead needs to exist: Pydantic rejects the payload before the
    # endpoint would ever look up lead_id.
    response = mock_client.patch(
        f"/api/v1/leads/{uuid.uuid4()}", json={"company_name": None}
    )

    assert response.status_code == 422


def test_update_lead_rejects_explicit_null_status(mock_client):
    response = mock_client.patch(f"/api/v1/leads/{uuid.uuid4()}", json={"status": None})

    assert response.status_code == 422
