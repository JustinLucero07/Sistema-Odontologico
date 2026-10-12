import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import Table, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.database import Base
from app.modules.audit.models import AuditLog
from app.modules.clinics.models import Clinic
from app.modules.patients.service import get_patient_or_404
from app.modules.privacy.constants import (
    ACCESS_DEDUP_MINUTES,
    CONFIDENTIALITY_VERSION,
    EXPORT_EXCLUDED_COLUMNS,
    PRIVACY_POLICY_VERSION,
)
from app.modules.privacy.models import DataConsent
from app.modules.privacy.schemas import ConsentCreate, ConsentOut, PrivacyStatus
from app.modules.users.models import User

# ---- Consentimientos ------------------------------------------------------


async def _user_names(db: AsyncSession, ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not ids:
        return {}
    rows = (await db.execute(select(User.id, User.first_name, User.last_name).where(User.id.in_(ids)))).all()
    return {row.id: f"{row.first_name} {row.last_name}" for row in rows}


async def privacy_status(db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID) -> PrivacyStatus:
    await get_patient_or_404(db, clinic_id, patient_id)
    rows = (
        (
            await db.execute(
                select(DataConsent)
                .where(DataConsent.clinic_id == clinic_id, DataConsent.patient_id == patient_id)
                .order_by(DataConsent.recorded_at.desc())
            )
        )
        .scalars()
        .all()
    )
    names = await _user_names(db, {r.recorded_by_id for r in rows if r.recorded_by_id})
    history = [
        ConsentOut.model_validate(r).model_copy(update={"recorded_by_name": names.get(r.recorded_by_id)})
        for r in rows
    ]
    notice = next((c for c in history if c.kind == "aviso_privacidad"), None)
    communications = next((c for c in history if c.kind == "comunicaciones"), None)
    return PrivacyStatus(
        current_policy_version=PRIVACY_POLICY_VERSION,
        privacy_notice=notice,
        communications=communications,
        notice_outdated=notice is not None and notice.policy_version != PRIVACY_POLICY_VERSION,
        history=history,
    )


async def record_consent(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, patient_id: uuid.UUID, payload: ConsentCreate
) -> DataConsent:
    patient = await get_patient_or_404(db, clinic_id, patient_id)
    if payload.kind == "aviso_privacidad" and not payload.granted:
        # Informar no se "retira": o se entregó el aviso o no.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El aviso de privacidad se registra como entregado; no se puede retirar.",
        )
    if patient.age is not None and patient.age < 18 and not (payload.signed_by_name or "").strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El paciente es menor de edad: indique el nombre de su representante legal.",
        )
    consent = DataConsent(
        clinic_id=clinic_id,
        patient_id=patient_id,
        kind=payload.kind,
        granted=payload.granted,
        policy_version=PRIVACY_POLICY_VERSION,
        method=payload.method,
        signed_by_name=(payload.signed_by_name or "").strip() or None,
        notes=payload.notes,
        recorded_by_id=actor_id,
        recorded_at=datetime.now(timezone.utc),
    )
    db.add(consent)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id,
        action="grant" if payload.granted else "revoke", entity_type="data_consent",
        entity_id=str(patient_id), after={"kind": payload.kind, "version": PRIVACY_POLICY_VERSION},
    )
    return consent


async def communications_revoked(db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID) -> bool:
    """True solo si el paciente RETIRÓ expresamente su autorización. Sin ningún
    registro se permite: los recordatorios de citas forman parte del servicio
    que el paciente pidió, pero en cuanto dice que no, se deja de enviar."""
    latest = (
        await db.execute(
            select(DataConsent.granted)
            .where(
                DataConsent.clinic_id == clinic_id,
                DataConsent.patient_id == patient_id,
                DataConsent.kind == "comunicaciones",
            )
            .order_by(DataConsent.recorded_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return latest is False


# ---- Registro de accesos -------------------------------------------------


async def log_patient_access(
    db: AsyncSession, clinic_id: uuid.UUID, user_id: uuid.UUID, patient_id: uuid.UUID, action: str = "view"
) -> None:
    """Deja constancia de quién abrió la ficha de un paciente. La historia
    clínica es confidencial: poder responder quién la vio es parte de
    protegerla."""
    since = datetime.now(timezone.utc) - timedelta(minutes=ACCESS_DEDUP_MINUTES)
    if action == "view":
        recent = await db.scalar(
            select(AuditLog.id).where(
                AuditLog.clinic_id == clinic_id,
                AuditLog.user_id == user_id,
                AuditLog.entity_type == "patient",
                AuditLog.entity_id == str(patient_id),
                AuditLog.action == "view",
                AuditLog.created_at >= since,
            ).limit(1)
        )
        if recent:
            return
    await record_audit(
        db, clinic_id=clinic_id, user_id=user_id, action=action, entity_type="patient", entity_id=str(patient_id)
    )


async def access_log(db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID, limit: int = 100) -> list[dict]:
    await get_patient_or_404(db, clinic_id, patient_id)
    rows = (
        await db.execute(
            select(AuditLog.created_at, AuditLog.action, User.first_name, User.last_name)
            .outerjoin(User, User.id == AuditLog.user_id)
            .where(
                AuditLog.clinic_id == clinic_id,
                AuditLog.entity_type.in_(("patient", "data_consent")),
                AuditLog.entity_id == str(patient_id),
            )
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
    ).all()
    return [
        {
            "at": r.created_at,
            "action": r.action,
            "user_name": f"{r.first_name} {r.last_name}" if r.first_name else None,
        }
        for r in rows
    ]


# ---- Exportación (derecho de acceso y portabilidad) -----------------------


def _json_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (uuid.UUID, Decimal)):
        return str(value)
    return value


def _row(table: Table, row) -> dict:
    return {
        column.name: _json_value(row._mapping[column])
        for column in table.columns
        if column.name not in EXPORT_EXCLUDED_COLUMNS
    }


async def export_patient_data(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, patient_id: uuid.UUID
) -> dict:
    """Todo lo que el sistema guarda de un paciente, en un formato legible por
    máquina. Se arma recorriendo el esquema en vez de una lista a mano: una
    tabla nueva con patient_id entra sola, y no se puede "olvidar" un módulo.

    Incluye las tablas hijas directas (ítems de receta, de presupuesto, eventos
    de laboratorio…) enlazadas por clave foránea a esas tablas."""
    patient = await get_patient_or_404(db, clinic_id, patient_id)
    tables = Base.metadata.tables

    owned = {
        name: table
        for name, table in tables.items()
        if "patient_id" in table.columns and "clinic_id" in table.columns
    }
    sections: dict[str, list[dict]] = {}
    ids_by_table: dict[str, list] = {}
    for name, table in sorted(owned.items()):
        rows = (
            await db.execute(
                select(table).where(table.c.patient_id == patient_id, table.c.clinic_id == clinic_id)
            )
        ).all()
        if rows:
            sections[name] = [_row(table, r) for r in rows]
            if "id" in table.columns:
                ids_by_table[name] = [r._mapping[table.c.id] for r in rows]

    # Un nivel más: filas que cuelgan de lo anterior sin tener patient_id.
    for name, table in sorted(tables.items()):
        if name in owned or name == "patients":
            continue
        for column in table.columns:
            for fk in column.foreign_keys:
                parent = fk.column.table.name
                if parent in ids_by_table and fk.column.name == "id":
                    rows = (
                        await db.execute(select(table).where(column.in_(ids_by_table[parent])))
                    ).all()
                    if rows:
                        sections.setdefault(name, []).extend(_row(table, r) for r in rows)

    clinic = await db.get(Clinic, clinic_id)
    await log_patient_access(db, clinic_id, actor_id, patient_id, action="export")
    return {
        "export": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "responsible": {
                "name": clinic.name if clinic else None,
                "legal_name": clinic.legal_name if clinic else None,
                "tax_id": clinic.tax_id if clinic else None,
            },
            "note": (
                "Copia de los datos personales y clínicos del paciente. Los archivos "
                "(radiografías, documentos) se entregan aparte; aquí figuran sus datos."
            ),
        },
        "patient": _row(tables["patients"], (await db.execute(
            select(tables["patients"]).where(tables["patients"].c.id == patient.id)
        )).one()),
        "records": sections,
    }


# ---- Personal ----------------------------------------------------------------


def confidentiality_required(user: User) -> bool:
    return user.confidentiality_version != CONFIDENTIALITY_VERSION


async def accept_confidentiality(db: AsyncSession, user: User) -> None:
    user.confidentiality_accepted_at = datetime.now(timezone.utc)
    user.confidentiality_version = CONFIDENTIALITY_VERSION
    await record_audit(
        db, clinic_id=user.clinic_id, user_id=user.id, action="accept", entity_type="confidentiality",
        entity_id=str(user.id), after={"version": CONFIDENTIALITY_VERSION},
    )


# ---------------------------------------------------------------------------
# Solicitudes de los titulares (derechos LOPDP)
# ---------------------------------------------------------------------------


def _rights_out(r, patient_name: str | None, today) -> dict:
    from app.modules.privacy.constants import RIGHTS_KINDS, RIGHTS_STATUSES

    abierta = r.status in ("pendiente", "en_proceso")
    return {
        **{k: getattr(r, k) for k in (
            "id", "patient_id", "requester_name", "requester_id_number", "contact", "kind", "details",
            "received_on", "due_on", "status", "response", "resolved_on", "created_at",
        )},
        "patient_name": patient_name,
        "kind_label": RIGHTS_KINDS.get(r.kind, r.kind),
        "status_label": RIGHTS_STATUSES.get(r.status, r.status),
        "overdue": abierta and r.due_on < today,
        "days_left": (r.due_on - today).days if abierta else None,
    }


async def list_rights_requests(db: AsyncSession, clinic_id: uuid.UUID) -> list[dict]:
    from datetime import date

    from app.modules.patients.models import Patient
    from app.modules.privacy.models import DataRightsRequest

    rows = (
        await db.execute(
            select(DataRightsRequest, Patient.first_name, Patient.last_name)
            .outerjoin(Patient, Patient.id == DataRightsRequest.patient_id)
            .where(DataRightsRequest.clinic_id == clinic_id)
            .order_by(DataRightsRequest.received_on.desc(), DataRightsRequest.created_at.desc())
        )
    ).all()
    hoy = date.today()
    return [_rights_out(r, f"{fn} {ln}" if fn else None, hoy) for r, fn, ln in rows]


async def _get_rights(db: AsyncSession, clinic_id: uuid.UUID, request_id: uuid.UUID):
    from fastapi import HTTPException

    from app.modules.privacy.models import DataRightsRequest

    r = await db.get(DataRightsRequest, request_id)
    if r is None or r.clinic_id != clinic_id:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return r


async def save_rights_request(
    db: AsyncSession, clinic_id: uuid.UUID, user_id: uuid.UUID, payload, request_id: uuid.UUID | None = None
) -> dict:
    from datetime import date, datetime, timedelta, timezone

    from app.core.audit import record_audit
    from app.modules.patients.models import Patient
    from app.modules.privacy.constants import RIGHTS_RESPONSE_DAYS
    from app.modules.privacy.models import DataRightsRequest

    data = payload.model_dump()
    if data["patient_id"]:
        p = await db.get(Patient, data["patient_id"])
        if p is None or p.clinic_id != clinic_id:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Paciente no encontrado")
    recibida = data.pop("received_on") or date.today()
    if request_id is None:
        r = DataRightsRequest(
            clinic_id=clinic_id, created_by_id=user_id, created_at=datetime.now(timezone.utc),
            received_on=recibida, due_on=recibida + timedelta(days=RIGHTS_RESPONSE_DAYS), **data,
        )
        db.add(r)
    else:
        r = await _get_rights(db, clinic_id, request_id)
        for k, v in data.items():
            setattr(r, k, v)
        if r.received_on != recibida:
            r.received_on = recibida
            r.due_on = recibida + timedelta(days=RIGHTS_RESPONSE_DAYS)
    if r.status in ("respondida", "rechazada"):
        r.resolved_on = r.resolved_on or date.today()
    else:
        r.resolved_on = None
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=user_id, action="create" if request_id is None else "update",
        entity_type="data_rights_request", entity_id=str(r.id), after=payload.model_dump(mode="json"),
    )
    nombre = None
    if r.patient_id:
        p = await db.get(Patient, r.patient_id)
        nombre = f"{p.first_name} {p.last_name}"
    return _rights_out(r, nombre, date.today())


async def delete_rights_request(db: AsyncSession, clinic_id: uuid.UUID, user_id: uuid.UUID, request_id: uuid.UUID):
    from app.core.audit import record_audit

    r = await _get_rights(db, clinic_id, request_id)
    await record_audit(
        db, clinic_id=clinic_id, user_id=user_id, action="delete", entity_type="data_rights_request",
        entity_id=str(r.id), before={"requester_name": r.requester_name, "kind": r.kind, "status": r.status},
    )
    await db.delete(r)
