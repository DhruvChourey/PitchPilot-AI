"""Cross-user ownership isolation tests -- two independently authenticated
users (the `client` and `second_client` fixtures), sharing the same
underlying DB transaction (so both users' data is visible within one
test) but with separate cookie jars/sessions. Verifies neither user can
read, update, or archive the other's leads, and that list/pagination
totals are scoped per-owner.
"""


def test_user_b_does_not_see_user_a_lead_in_list(client, second_client, lead_payload):
    client.post("/api/v1/leads", json=lead_payload)

    response = second_client.get("/api/v1/leads")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []


def test_user_b_cannot_get_user_a_lead(client, second_client, lead_payload):
    created = client.post("/api/v1/leads", json=lead_payload).json()

    response = second_client.get(f"/api/v1/leads/{created['id']}")

    assert response.status_code == 404


def test_user_a_can_still_get_own_lead(client, second_client, lead_payload):
    created = client.post("/api/v1/leads", json=lead_payload).json()

    response = client.get(f"/api/v1/leads/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_user_b_cannot_update_user_a_lead(client, second_client, lead_payload):
    created = client.post("/api/v1/leads", json=lead_payload).json()

    response = second_client.patch(
        f"/api/v1/leads/{created['id']}", json={"industry": "Hijacked"}
    )
    assert response.status_code == 404

    # A's lead must be completely unaffected.
    refreshed = client.get(f"/api/v1/leads/{created['id']}").json()
    assert refreshed["industry"] == lead_payload["industry"]


def test_user_b_cannot_archive_user_a_lead(client, second_client, lead_payload):
    created = client.post("/api/v1/leads", json=lead_payload).json()

    response = second_client.delete(f"/api/v1/leads/{created['id']}")
    assert response.status_code == 404

    # A's lead must still be exactly as it was -- not archived.
    refreshed = client.get(f"/api/v1/leads/{created['id']}").json()
    assert refreshed["status"] == "new"


def test_pagination_totals_scoped_per_owner(client, second_client, lead_payload):
    for _ in range(3):
        client.post("/api/v1/leads", json={**lead_payload, "company_name": "A Co"})
    for _ in range(2):
        second_client.post("/api/v1/leads", json={**lead_payload, "company_name": "B Co"})

    a_list = client.get("/api/v1/leads").json()
    b_list = second_client.get("/api/v1/leads").json()

    assert a_list["total"] == 3
    assert all(item["company_name"] == "A Co" for item in a_list["items"])
    assert b_list["total"] == 2
    assert all(item["company_name"] == "B Co" for item in b_list["items"])


def test_status_filter_still_scoped_to_owner(client, second_client, lead_payload):
    a_lead = client.post("/api/v1/leads", json=lead_payload).json()
    client.patch(f"/api/v1/leads/{a_lead['id']}", json={"status": "researching"})

    b_lead = second_client.post("/api/v1/leads", json=lead_payload).json()
    second_client.patch(f"/api/v1/leads/{b_lead['id']}", json={"status": "researching"})

    # Both users have one "researching" lead, but each should only see
    # their own when filtering by status.
    a_filtered = client.get("/api/v1/leads", params={"status": "researching"}).json()
    b_filtered = second_client.get("/api/v1/leads", params={"status": "researching"}).json()

    assert a_filtered["total"] == 1
    assert a_filtered["items"][0]["id"] == a_lead["id"]
    assert b_filtered["total"] == 1
    assert b_filtered["items"][0]["id"] == b_lead["id"]


def test_create_lead_owner_set_from_session_not_client_input(client, lead_payload):
    # LeadCreate never exposes an owner_id field at all, so there's
    # nothing a client could send to influence it -- confirm a bogus
    # owner_id in the request body is simply ignored (422 would also be
    # an acceptable outcome; what matters is it's never taken as the
    # actual owner).
    payload = {**lead_payload, "owner_id": "00000000-0000-0000-0000-000000000000"}

    response = client.post("/api/v1/leads", json=payload)

    assert response.status_code == 201
    # LeadRead never includes owner_id, so there's no field to leak it
    # through even if the client-supplied value had been used.
    assert "owner_id" not in response.json()
    # The lead must be visible to the actual authenticated creator --
    # proves owner_id came from the session, not the (ignored) payload
    # value, since that bogus UUID belongs to no real user.
    list_response = client.get("/api/v1/leads").json()
    assert any(item["id"] == response.json()["id"] for item in list_response["items"])
