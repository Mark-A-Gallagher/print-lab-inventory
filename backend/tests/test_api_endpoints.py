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


def test_spool_includes_material_type_and_color(client):
    material_id = _make_material(client)
    petg = _make_spool(client, material_id, material_type="PETG", color="Blue")
    other = _make_spool(client, material_id, material_type="ABS", color="Black")

    first = client.get(f"/spools/{petg['id']}").json()
    second = client.get(f"/spools/{other['id']}").json()

    # Creating the second spool must not change the first one's type/color.
    assert (first["material_type"], first["color"]) == ("PETG", "Blue")
    assert (second["material_type"], second["color"]) == ("ABS", "Black")


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
