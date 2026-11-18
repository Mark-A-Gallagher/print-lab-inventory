# test_api_endpoints.py
#
# Endpoint-level tests (request body shapes, status codes) for the
# reserve, unassign, spool material, and machine delete endpoints.

from app.models import Material


def _make_material(client, name="PLA", color="Red") -> int:
    with client.session_factory() as session:
        material = Material(name=name, color=color)
        session.add(material)
        session.commit()
        return material.id


def _make_spool(client, material_id: int, **extra) -> dict:
    payload = {
        "material_id": material_id,
        "original_weight": 1000,
        "empty_spool_weight": 100,
        "low_stock_threshold": 200,
        **extra,
    }
    response = client.post("/spools/", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _make_machine(client, name="Printer 1") -> dict:
    response = client.post("/machines/", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


def test_reserve_accepts_spool_id_amount_and_user(client):
    material_id = _make_material(client)
    spool = _make_spool(client, material_id)
    request = client.post(
        "/requests/",
        json={
            "requested_by": "alice",
            "project_name": "Toy Truck",
            "material_id": material_id,
            "amount_grams": 100,
        },
    ).json()

    response = client.post(
        f"/requests/{request['id']}/reserve",
        json={"spool_id": spool["id"], "amount": 100, "user_id": "system"},
    )

    assert response.status_code == 201, response.text
    assert response.json()["spool_id"] == spool["id"]
    assert response.json()["print_request_id"] == request["id"]
    assert client.get(f"/spools/{spool['id']}").json()["reserved_amount"] == 100


def test_unassign_only_needs_user_id(client):
    spool = _make_spool(client, _make_material(client))
    machine = _make_machine(client)
    client.post(
        f"/spools/{spool['id']}/assign",
        json={"machine_id": machine["id"], "user_id": "system"},
    )

    response = client.post(
        f"/spools/{spool['id']}/unassign", json={"user_id": "system"}
    )

    assert response.status_code == 204, response.text
    assert client.get(f"/spools/{spool['id']}").json()["current_machine_id"] is None


def test_spool_uses_entered_id_as_physical_spool_id(client):
    response = client.post(
        "/spools/",
        json={
            "id": 42,
            "material_type": "PLA",
            "color": "Green",
            "original_weight": 1000,
            "empty_spool_weight": 100,
            "low_stock_threshold": 200,
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["id"] == 42

    duplicate = client.post(
        "/spools/",
        json={
            "id": 42,
            "material_type": "PETG",
            "color": "Blue",
            "original_weight": 1000,
            "empty_spool_weight": 100,
            "low_stock_threshold": 200,
        },
    )
    assert duplicate.status_code == 422


def test_delete_machine_without_history_removes_it(client):
    machine = _make_machine(client)

    assert client.delete(f"/machines/{machine['id']}").status_code == 204
    assert client.get("/machines/").json() == []
    assert client.get(f"/machines/{machine['id']}").status_code == 404


def test_delete_machine_with_history_retires_it(client):
    spool = _make_spool(client, _make_material(client))
    machine = _make_machine(client)
    body = {"machine_id": machine["id"], "user_id": "system"}
    client.post(f"/spools/{spool['id']}/assign", json=body)
    client.post(f"/spools/{spool['id']}/unassign", json={"user_id": "system"})

    assert client.delete(f"/machines/{machine['id']}").status_code == 204
    assert client.get("/machines/").json() == []
    # A retired machine can't receive spools either.
    assert client.post(f"/spools/{spool['id']}/assign", json=body).status_code == 404


def test_delete_machine_with_assigned_spool_is_rejected(client):
    spool = _make_spool(client, _make_material(client))
    machine = _make_machine(client)
    client.post(
        f"/spools/{spool['id']}/assign",
        json={"machine_id": machine["id"], "user_id": "system"},
    )

    assert client.delete(f"/machines/{machine['id']}").status_code == 422
    assert len(client.get("/machines/").json()) == 1


def test_ticket_uses_entered_number_and_tracks_color_count(client):
    response = client.post(
        "/requests/",
        json={
            "id": 1234,
            "requested_by": "alice",
            "project_name": "Multi-color Project",
            "amount_grams": 150,
            "color_count": 3,
        },
    )

    assert response.status_code == 201, response.text
    ticket = response.json()
    assert ticket["id"] == 1234
    assert ticket["amount_grams"] == 150
    assert ticket["color_count"] == 3


def test_ticket_reservation_lock_status_and_completion(client):
    material_id = _make_material(client)
    spool = _make_spool(client, material_id)

    ticket_response = client.post(
        "/requests/",
        json={
            "id": 3001,
            "requested_by": "alice",
            "project_name": "Locked Print",
            "amount_grams": 120,
            "color_count": 2,
        },
    )
    assert ticket_response.status_code == 201, ticket_response.text

    batch = client.post(
        "/requests/3001/reserve-batch",
        json={
            "allocations": [
                {"spool_id": spool["id"], "amount": 70},
                {"spool_id": spool["id"], "amount": 50},
            ],
            "user_id": "system",
        },
    )
    assert batch.status_code == 201, batch.text

    repeat = client.post(
        "/requests/3001/reserve-batch",
        json={
            "allocations": [{"spool_id": spool["id"], "amount": 10}],
            "user_id": "system",
        },
    )
    assert repeat.status_code == 422

    reservations = client.get("/requests/3001/reservations")
    assert reservations.status_code == 200
    assert sum(item["amount"] for item in reservations.json()) == 120

    active = client.patch("/requests/3001/status", json={"status": "Printing"})
    assert active.status_code == 200, active.text

    complete = client.post("/requests/3001/complete")
    assert complete.status_code == 200, complete.text
    assert complete.json()["status"] == "Complete"

    spool_after = client.get(f"/spools/{spool['id']}")
    assert spool_after.status_code == 200
    assert spool_after.json()["reserved_amount"] == 0
    assert spool_after.json()["current_weight"] == 880


def test_ticket_reservations_cannot_exceed_total(client):
    ticket = client.post(
        "/requests/",
        json={
            "id": 2001,
            "requested_by": "bob",
            "project_name": "Small Project",
            "amount_grams": 100,
            "color_count": 2,
        },
    ).json()

    material_id = _make_material(client)
    spool = _make_spool(client, material_id)

    first = client.post(
        f"/requests/{ticket['id']}/reserve",
        json={"spool_id": spool["id"], "amount": 70, "user_id": "system"},
    )
    assert first.status_code == 201, first.text

    second = client.post(
        f"/requests/{ticket['id']}/reserve",
        json={"spool_id": spool["id"], "amount": 40, "user_id": "system"},
    )
    assert second.status_code == 422
