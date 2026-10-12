"""Lead API tests that require a real, isolated PostgreSQL TEST_DATABASE_URL.

These exercise actual persistence, pagination, filtering, and 404 lookups
against a live database (see conftest.py's test_engine/db_session fixtures).
They are skipped if TEST_DATABASE_URL is not configured, and refuse to run
at all (pytest.exit) if TEST_DATABASE_URL equals DATABASE_URL, since the
session-scoped test_engine fixture calls Base.metadata.drop_all() at
teardown.

Pure request-validation tests that never need the endpoint body to execute
live in test_leads_validation.py instead, using a mocked DB session.
"""

import uuid


def test_create_lead_success(client, lead_payload):
    response = client.post("/api/v1/leads", json=lead_payload)

    assert response.status_code == 201
    body = response.json()
    assert body["company_name"] == lead_payload["company_name"]
    assert body["status"] == "new"
    assert body["id"]
    assert body["created_at"]
    assert body["updated_at"]


def test_list_leads_and_pagination(client, lead_payload):
    for _ in range(3):
        payload = {**lead_payload, "company_name": f"Company {uuid.uuid4().hex[:8]}"}
        assert client.post("/api/v1/leads", json=payload).status_code == 201

    response = client.get("/api/v1/leads", params={"page": 1, "page_size": 2})

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert len(body["items"]) == 2
    assert body["total"] >= 3


def test_list_leads_filters_by_status(client, lead_payload):
    created = client.post("/api/v1/leads", json=lead_payload).json()
    client.patch(f"/api/v1/leads/{created['id']}", json={"status": "researching"})

    response = client.get("/api/v1/leads", params={"status": "researching"})

    assert response.status_code == 200
    body = response.json()
    assert all(item["status"] == "researching" for item in body["items"])
    assert any(item["id"] == created["id"] for item in body["items"])


def test_get_lead_success(client, lead_payload):
    created = client.post("/api/v1/leads", json=lead_payload).json()

    response = client.get(f"/api/v1/leads/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_lead_not_found(client):
    response = client.get(f"/api/v1/leads/{uuid.uuid4()}")

    assert response.status_code == 404


def test_update_lead_only_supplied_fields(client, lead_payload):
    created = client.post("/api/v1/leads", json=lead_payload).json()

    response = client.patch(
        f"/api/v1/leads/{created['id']}", json={"industry": "Finance"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["industry"] == "Finance"
    assert body["company_name"] == lead_payload["company_name"]
    assert body["contact_email"] == lead_payload["contact_email"]


def test_update_lead_allows_explicit_null_for_nullable_field(client, lead_payload):
    created = client.post("/api/v1/leads", json=lead_payload).json()

    response = client.patch(
        f"/api/v1/leads/{created['id']}", json={"industry": None}
    )

    assert response.status_code == 200
    assert response.json()["industry"] is None


def test_update_lead_not_found(client):
    response = client.patch(
        f"/api/v1/leads/{uuid.uuid4()}", json={"industry": "Finance"}
    )

    assert response.status_code == 404


def test_archive_lead(client, lead_payload):
    created = client.post("/api/v1/leads", json=lead_payload).json()

    response = client.delete(f"/api/v1/leads/{created['id']}")

    assert response.status_code == 200
    assert response.json()["status"] == "archived"

    refreshed = client.get(f"/api/v1/leads/{created['id']}")
    assert refreshed.status_code == 200
    assert refreshed.json()["status"] == "archived"


def test_archive_lead_not_found(client):
    response = client.delete(f"/api/v1/leads/{uuid.uuid4()}")

    assert response.status_code == 404


def test_lead_persists_with_correct_defaults(client, lead_payload):
    created = client.post("/api/v1/leads", json=lead_payload).json()

    fetched = client.get(f"/api/v1/leads/{created['id']}").json()

    assert fetched["status"] == "new"
    assert fetched["id"] == created["id"]
    assert fetched["created_at"] == created["created_at"]
