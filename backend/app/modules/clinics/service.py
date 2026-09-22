import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.modules.clinics.models import Branch, Clinic, Operatory
from app.modules.clinics.schemas import BranchCreate, BranchUpdate, ClinicUpdate, OperatoryCreate, OperatoryUpdate


async def get_clinic_or_404(db: AsyncSession, clinic_id: uuid.UUID) -> Clinic:
    clinic = await db.get(Clinic, clinic_id)
    if clinic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clínica no encontrada")
    return clinic


async def update_clinic(db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, payload: ClinicUpdate) -> Clinic:
    clinic = await get_clinic_or_404(db, clinic_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(clinic, field, value)
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="update", entity_type="clinic", entity_id=str(clinic_id),
        after=data,
    )
    return clinic


async def list_branches(db: AsyncSession, clinic_id: uuid.UUID) -> list[Branch]:
    result = await db.execute(select(Branch).where(Branch.clinic_id == clinic_id).order_by(Branch.name))
    return list(result.scalars().all())


async def create_branch(db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, payload: BranchCreate) -> Branch:
    branch = Branch(clinic_id=clinic_id, **payload.model_dump())
    db.add(branch)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="branch", entity_id=str(branch.id),
        after=payload.model_dump(),
    )
    return branch


async def get_branch_or_404(db: AsyncSession, clinic_id: uuid.UUID, branch_id: uuid.UUID) -> Branch:
    result = await db.execute(select(Branch).where(Branch.id == branch_id, Branch.clinic_id == clinic_id))
    branch = result.scalar_one_or_none()
    if branch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada")
    return branch


async def update_branch(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, branch_id: uuid.UUID, payload: BranchUpdate
) -> Branch:
    branch = await get_branch_or_404(db, clinic_id, branch_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(branch, field, value)
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="update", entity_type="branch", entity_id=str(branch_id),
        after=data,
    )
    return branch


async def delete_branch(db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, branch_id: uuid.UUID) -> None:
    branch = await get_branch_or_404(db, clinic_id, branch_id)
    rooms = await db.scalar(select(func.count()).select_from(Operatory).where(Operatory.branch_id == branch_id))
    if rooms:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"La sede tiene {rooms} consultorio(s). Elimínelos o desactívelos primero.",
        )
    await db.delete(branch)
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="delete", entity_type="branch", entity_id=str(branch_id),
    )


async def list_operatories(db: AsyncSession, clinic_id: uuid.UUID) -> list[Operatory]:
    result = await db.execute(select(Operatory).where(Operatory.clinic_id == clinic_id).order_by(Operatory.name))
    return list(result.scalars().all())


async def create_operatory(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, payload: OperatoryCreate
) -> Operatory:
    await get_branch_or_404(db, clinic_id, payload.branch_id)
    operatory = Operatory(clinic_id=clinic_id, **payload.model_dump())
    db.add(operatory)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="operatory",
        entity_id=str(operatory.id), after=payload.model_dump(mode="json"),
    )
    return operatory


async def delete_operatory(db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, operatory_id: uuid.UUID) -> None:
    result = await db.execute(
        select(Operatory).where(Operatory.id == operatory_id, Operatory.clinic_id == clinic_id)
    )
    operatory = result.scalar_one_or_none()
    if operatory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultorio no encontrado")
    # Importado aquí para no crear un ciclo entre módulos al cargar.
    from app.modules.appointments.models import Appointment

    used = await db.scalar(
        select(func.count()).select_from(Appointment).where(Appointment.operatory_id == operatory_id)
    )
    if used:
        # Las citas pasadas lo nombran; se retira en vez de borrarlo.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tiene {used} cita(s) registradas. Desactívelo en lugar de eliminarlo.",
        )
    await db.delete(operatory)
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="delete", entity_type="operatory",
        entity_id=str(operatory_id),
    )


async def update_operatory(
    db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, operatory_id: uuid.UUID, payload: OperatoryUpdate
) -> Operatory:
    operatory = (
        await db.execute(select(Operatory).where(Operatory.id == operatory_id, Operatory.clinic_id == clinic_id))
    ).scalar_one_or_none()
    if operatory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultorio no encontrado")
    data = payload.model_dump(exclude_unset=True)
    if "branch_id" in data:
        await get_branch_or_404(db, clinic_id, data["branch_id"])
    for field, value in data.items():
        setattr(operatory, field, value)
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="update", entity_type="operatory",
        entity_id=str(operatory_id), after=data,
    )
    return operatory
