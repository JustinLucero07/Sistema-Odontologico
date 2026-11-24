import io

from PIL import Image


async def _h(client, email="admin@clinicatest.io", password="Admin123!"):
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _png(color="white") -> bytes:
    b = io.BytesIO()
    Image.new("RGB", (40, 30), color).save(b, "PNG")
    return b.getvalue()


async def _foto(client, h, pid, titulo, color):
    r = await client.post(
        f"/api/v1/patients/{pid}/images",
        files={"file": (f"{titulo}.png", io.BytesIO(_png(color)), "image/png")},
        data={"image_type": "foto_intraoral", "title": titulo},
        headers=h,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def test_crear_editar_y_borrar(client):
    h = await _h(client)
    pid = (await client.post("/api/v1/patients", json={"first_name": "Ana", "last_name": "Mora"}, headers=h)).json()["id"]
    otro = (await client.post("/api/v1/patients", json={"first_name": "Luis", "last_name": "Paz"}, headers=h)).json()["id"]
    antes = await _foto(client, h, pid, "Antes", "yellow")
    despues = await _foto(client, h, pid, "Despues", "white")
    ajena = await _foto(client, h, otro, "Ajena", "gray")

    base = f"/api/v1/patients/{pid}/comparisons"
    r = await client.post(base, json={"before_image_id": antes, "after_image_id": antes, "title": "X"}, headers=h)
    assert r.status_code == 422
    r = await client.post(base, json={"before_image_id": antes, "after_image_id": ajena, "title": "X"}, headers=h)
    assert r.status_code == 422

    r = await client.post(
        base,
        json={"before_image_id": antes, "after_image_id": despues, "title": "Blanqueamiento", "treatment": "Blanqueamiento"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    c = r.json()
    assert c["before"]["title"] == "Antes" and c["after"]["title"] == "Despues"
    assert c["share_consent"] is False and c["share_consent_at"] is None

    # Autorizar a compartir deja la fecha; retirarla la quita.
    r = await client.put(f"/api/v1/comparisons/{c['id']}", json={"share_consent": True}, headers=h)
    assert r.json()["share_consent"] is True and r.json()["share_consent_at"]
    r = await client.put(f"/api/v1/comparisons/{c['id']}", json={"share_consent": False, "title": "Carillas"}, headers=h)
    assert r.json()["share_consent_at"] is None and r.json()["title"] == "Carillas"

    assert len((await client.get(base, headers=h)).json()) == 1
    assert (await client.delete(f"/api/v1/comparisons/{c['id']}", headers=h)).status_code == 204
    assert (await client.get(base, headers=h)).json() == []
    # Las fotos siguen en la historia.
    assert len((await client.get(f"/api/v1/patients/{pid}/images", headers=h)).json()) == 2
