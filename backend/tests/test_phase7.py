"""Phase 7: periodontal charting and clinical imaging.

The tests here are about the two guarantees the phase exists to make — that a
periodontal exam can never be silently corrupted by a duplicated site, and that
an image is withdrawn rather than destroyed.
"""

import io


async def _login(client, email, password):
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_patient(client, token, first_name="Elena") -> str:
    created = await client.post(
        "/api/v1/patients",
        json={"first_name": first_name, "last_name": "Rivas"},
        headers=_auth(token),
    )
    return created.json()["id"]


def _sites(fdi: str, depths: list[int], bleeding: list[bool] | None = None) -> list[dict]:
    codes = [
        "vestibular_distal",
        "vestibular_central",
        "vestibular_mesial",
        "lingual_distal",
        "lingual_central",
        "lingual_mesial",
    ]
    bleeding = bleeding or [False] * 6
    return [
        {"fdi_number": fdi, "site": code, "probing_depth": d, "recession": 0, "bleeding": b}
        for code, d, b in zip(codes, depths, bleeding)
    ]


# ---- Periodontogram ------------------------------------------------------


async def test_create_periodontogram_and_compute_indices(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    measurements = _sites("16", [3, 2, 4, 5, 3, 6], [True, False, True, False, False, True])
    measurements += _sites("26", [2, 2, 2, 2, 2, 2])

    created = await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram",
        json={
            "notes": "Examen inicial",
            "teeth": [{"fdi_number": "16", "mobility": 1, "furcation": 1}],
            "measurements": measurements,
        },
        headers=_auth(token),
    )
    assert created.status_code == 201, created.text

    body = created.json()
    assert body["type"] == "initial"
    indices = body["indices"]
    assert indices["sites_recorded"] == 12
    assert indices["bleeding_sites"] == 3
    assert indices["bleeding_index"] == 25.0
    assert indices["max_probing_depth"] == 6
    assert indices["sites_over_3mm"] == 3  # 4, 5 and 6 mm
    assert indices["sites_over_5mm"] == 1


async def test_attachment_level_is_derived_not_stored(client, clinic_with_users):
    """CAL = probing depth + recession. It is computed on the way out so it can
    never disagree with the two numbers it comes from."""
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram",
        json={
            "measurements": [
                {
                    "fdi_number": "11",
                    "site": "vestibular_central",
                    "probing_depth": 4,
                    "recession": 2,
                },
                # No recession recorded: CAL is unknown, not zero.
                {"fdi_number": "21", "site": "vestibular_central", "probing_depth": 3},
            ]
        },
        headers=_auth(token),
    )
    by_tooth = {m["fdi_number"]: m for m in created.json()["measurements"]}
    assert by_tooth["11"]["attachment_level"] == 6
    assert by_tooth["21"]["attachment_level"] is None


async def test_duplicate_site_is_rejected(client, clinic_with_users):
    """Two readings for the same site would silently halve every index."""
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram",
        json={
            "measurements": [
                {"fdi_number": "16", "site": "vestibular_central", "probing_depth": 3},
                {"fdi_number": "16", "site": "vestibular_central", "probing_depth": 5},
            ]
        },
        headers=_auth(token),
    )
    assert response.status_code == 422
    assert "duplicada" in response.json()["detail"].lower()


async def test_out_of_range_probing_depth_is_rejected(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram",
        json={
            "measurements": [
                {"fdi_number": "16", "site": "vestibular_central", "probing_depth": 40}
            ]
        },
        headers=_auth(token),
    )
    assert response.status_code == 422


async def test_periodontogram_versions_are_append_only(client, clinic_with_users):
    """A second exam chains to the first instead of replacing it — comparing
    pocket depths over time is the whole point of the chart."""
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    first = await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram",
        json={"measurements": _sites("16", [5, 5, 5, 5, 5, 5])},
        headers=_auth(token),
    )
    second = await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram",
        json={"measurements": _sites("16", [3, 3, 3, 3, 3, 3])},
        headers=_auth(token),
    )
    assert second.json()["previous_periodontogram_id"] == first.json()["id"]
    assert second.json()["type"] == "followup"

    versions = await client.get(
        f"/api/v1/patients/{patient_id}/periodontogram/versions", headers=_auth(token)
    )
    assert len(versions.json()) == 2

    # The earlier exam still reads back with its original numbers.
    original = await client.get(
        f"/api/v1/patients/{patient_id}/periodontogram/{first.json()['id']}",
        headers=_auth(token),
    )
    assert original.json()["indices"]["mean_probing_depth"] == 5.0


# ---- Clinical imaging ----------------------------------------------------


def _png_bytes() -> bytes:
    """A 1×1 PNG, hand-built so the test has no image library dependency."""
    import struct
    import zlib

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    idat = zlib.compress(b"\x00\xff\xff\xff")
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


async def test_upload_image_reads_its_dimensions(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/images",
        files={"file": ("periapical.png", io.BytesIO(_png_bytes()), "image/png")},
        data={
            "title": "Periapical 16",
            "image_type": "periapical",
            "fdi_numbers": "16,17",
            "taken_on": "2026-01-15",
        },
        headers=_auth(token),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["width"] == 1 and body["height"] == 1
    assert body["fdi_numbers"] == ["16", "17"]
    assert body["taken_on"] == "2026-01-15"


async def test_non_image_upload_is_refused(client, clinic_with_users):
    """A PDF would upload happily and then show the viewer a blank frame."""
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/images",
        files={"file": ("informe.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
        data={"title": "Informe", "image_type": "otro"},
        headers=_auth(token),
    )
    assert response.status_code == 400


async def test_invalid_fdi_number_is_refused(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/images",
        files={"file": ("rx.png", io.BytesIO(_png_bytes()), "image/png")},
        data={"title": "Rx", "image_type": "periapical", "fdi_numbers": "16,99"},
        headers=_auth(token),
    )
    assert response.status_code == 400
    assert "99" in response.json()["detail"]


async def test_future_study_date_is_refused(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/images",
        files={"file": ("rx.png", io.BytesIO(_png_bytes()), "image/png")},
        data={"title": "Rx", "image_type": "panoramica", "taken_on": "2099-01-01"},
        headers=_auth(token),
    )
    assert response.status_code == 400


async def test_archiving_hides_the_image_without_destroying_it(client, clinic_with_users):
    """An image acted on clinically stays in the record even once withdrawn —
    proving which image was seen at the time is what the archive is for."""
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)

    uploaded = await client.post(
        f"/api/v1/patients/{patient_id}/images",
        files={"file": ("rx.png", io.BytesIO(_png_bytes()), "image/png")},
        data={"title": "Panorámica", "image_type": "panoramica"},
        headers=_auth(token),
    )
    image_id = uploaded.json()["id"]

    archived = await client.post(
        f"/api/v1/images/{image_id}/archive",
        json={"reason": "Corresponde a otro paciente"},
        headers=_auth(token),
    )
    assert archived.status_code == 200
    assert archived.json()["archived_reason"] == "Corresponde a otro paciente"

    active = await client.get(f"/api/v1/patients/{patient_id}/images", headers=_auth(token))
    assert active.json() == []

    everything = await client.get(
        f"/api/v1/patients/{patient_id}/images?include_archived=true", headers=_auth(token)
    )
    assert len(everything.json()) == 1

    # The bytes are still served: the study was not destroyed.
    still_there = await client.get(f"/api/v1/images/{image_id}/file", headers=_auth(token))
    assert still_there.status_code == 200


async def test_archive_requires_a_reason(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)
    uploaded = await client.post(
        f"/api/v1/patients/{patient_id}/images",
        files={"file": ("rx.png", io.BytesIO(_png_bytes()), "image/png")},
        data={"title": "Rx", "image_type": "panoramica"},
        headers=_auth(token),
    )

    response = await client.post(
        f"/api/v1/images/{uploaded.json()['id']}/archive",
        json={"reason": "   "},
        headers=_auth(token),
    )
    assert response.status_code == 400


async def test_images_have_no_delete_endpoint(client, clinic_with_users):
    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)
    uploaded = await client.post(
        f"/api/v1/patients/{patient_id}/images",
        files={"file": ("rx.png", io.BytesIO(_png_bytes()), "image/png")},
        data={"title": "Rx", "image_type": "panoramica"},
        headers=_auth(token),
    )

    image_id = uploaded.json()["id"]
    deleted = await client.delete(f"/api/v1/images/{image_id}", headers=_auth(token))
    # 404 rather than 405: the path does not exist at all, because no handler
    # was ever written for it. Either way the point is that the call fails and
    # the study survives — archiving is the only way out.
    assert deleted.status_code in (404, 405)

    survivors = await client.get(
        f"/api/v1/patients/{patient_id}/images", headers=_auth(token)
    )
    assert [i["id"] for i in survivors.json()] == [image_id]


async def test_reading_an_image_is_audited(client, clinic_with_users, db_session):
    from sqlalchemy import select

    from app.modules.audit.models import AuditLog

    token = await _login(client, "admin@clinicatest.io", "Admin123!")
    patient_id = await _create_patient(client, token)
    uploaded = await client.post(
        f"/api/v1/patients/{patient_id}/images",
        files={"file": ("rx.png", io.BytesIO(_png_bytes()), "image/png")},
        data={"title": "Panorámica", "image_type": "panoramica"},
        headers=_auth(token),
    )
    image_id = uploaded.json()["id"]
    await client.get(f"/api/v1/images/{image_id}/file", headers=_auth(token))

    result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.entity_type == "clinical_image", AuditLog.action == "download"
        )
    )
    assert result.scalars().first() is not None
