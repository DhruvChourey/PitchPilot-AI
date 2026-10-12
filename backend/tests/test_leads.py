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


def test_create_lead_missing_company_name(client, lead_payload):
    payload = {**lead_payload}
    del payload["company_name"]

    response = client.post("/api/v1/leads", json=payload)

    assert response.status_code == 422


def test_create_lead_blank_company_name(client, lead_payload):
    payload = {**lead_payload, "company_name": "   "}

    response = client.post("/api/v1/leads", json=payload)

    assert response.status_code == 422


def test_create_lead_invalid_email(client, lead_payload):
    payload = {**lead_payload, "contact_email": "not-an-email"}

    response = client.post("/api/v1/leads", json=payload)

    assert response.status_code == 422


def test_create_lead_invalid_website(client, lead_payload):
    payload = {**lead_payload, "website": "not-a-url"}

    response = client.post("/api/v1/leads", json=payload)

    assert response.status_code == 422


def test_create_lead_invalid_status(client, lead_payload):
    payload = {**lead_payload, "status": "not-a-real-status"}

    response = client.post("/api/v1/leads", json=payload)

    assert response.status_code == 422


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


def test_update_lead_rejects_explicit_null_company_name(client, lead_payload):
    created = client.post("/api/v1/leads", json=lead_payload).json()

    response = client.patch(
        f"/api/v1/leads/{created['id']}", json={"company_name": None}
    )

    assert response.status_code == 422


def test_update_lead_rejects_explicit_null_status(client, lead_payload):
    created = client.post("/api/v1/leads", json=lead_payload).json()

    response = client.patch(f"/api/v1/leads/{created['id']}", json={"status": None})

    assert response.status_code == 422


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
