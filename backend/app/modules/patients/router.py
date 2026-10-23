import uuid

from fastapi import Response, APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.patients import service
from app.modules.patients.schemas import PatientCreate, PatientListItem, PatientOut, PatientUpdate

router = APIRouter(prefix="/api/v1/patients", tags=["patients"])


@router.get("", response_model=list[PatientListItem])
async def get_patients(
    response: Response,
    search: str | None = Query(default=None),
    limit: int = Query(default=300, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("patients:read")),
):
    # Paginado: una clínica con miles de pacientes no descarga la lista entera
    # en cada apertura (en el celular, con datos móviles, eso pesa). El total
    # va en X-Total-Count; la búsqueda encuentra a cualquiera.
    pacientes, total = await service.list_patients(db, current_user.clinic_id, search, limit, offset)
    response.headers["X-Total-Count"] = str(total)
    return pacientes


@router.post("", response_model=PatientOut, status_code=201)
async def post_patient(
    payload: PatientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("patients:write")),
):
    patient = await service.create_patient(db, current_user.clinic_id, current_user.id, payload)
    await db.commit()
    return patient


@router.get("/{patient_id}", response_model=PatientOut)
async def get_patient(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("patients:read")),
):
    patient = await service.get_patient_or_404(db, current_user.clinic_id, patient_id)
    # Quién abrió esta ficha queda registrado: la historia es confidencial.
    from app.modules.privacy.service import log_patient_access

    await log_patient_access(db, current_user.clinic_id, current_user.id, patient_id)
    await db.commit()
    return patient


@router.put("/{patient_id}", response_model=PatientOut)
async def put_patient(
    patient_id: uuid.UUID,
    payload: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("patients:write")),
):
    patient = await service.update_patient(db, current_user.clinic_id, current_user.id, patient_id, payload)
    await db.commit()
    return patient


@router.delete("/{patient_id}", status_code=204)
async def remove_patient(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("patients:delete")),
):
    await service.deactivate_patient(db, current_user.clinic_id, current_user.id, patient_id)
    await db.commit()
