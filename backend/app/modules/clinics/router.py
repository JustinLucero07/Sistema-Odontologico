import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.clinics import service
from app.modules.clinics.schemas import (
    BranchCreate,
    BranchOut,
    BranchUpdate,
    ClinicOut,
    ClinicUpdate,
    OperatoryCreate,
    OperatoryUpdate,
    OperatoryOut,
)

router = APIRouter(prefix="/api/v1/clinics", tags=["clinics"])


@router.get("/me", response_model=ClinicOut)
async def get_my_clinic(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings:manage")),
):
    return await service.get_clinic_or_404(db, current_user.clinic_id)


@router.put("/me", response_model=ClinicOut)
async def put_my_clinic(
    payload: ClinicUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings:manage")),
):
    clinic = await service.update_clinic(db, current_user.clinic_id, current_user.id, payload)
    await db.commit()
    return clinic


@router.get("/branches", response_model=list[BranchOut])
async def get_branches(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings:manage")),
):
    return await service.list_branches(db, current_user.clinic_id)


@router.post("/branches", response_model=BranchOut, status_code=201)
async def post_branch(
    payload: BranchCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings:manage")),
):
    branch = await service.create_branch(db, current_user.clinic_id, current_user.id, payload)
    await db.commit()
    return branch


@router.put("/branches/{branch_id}", response_model=BranchOut)
async def put_branch(
    branch_id: uuid.UUID,
    payload: BranchUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings:manage")),
):
    branch = await service.update_branch(db, current_user.clinic_id, current_user.id, branch_id, payload)
    await db.commit()
    return branch


@router.delete("/branches/{branch_id}", status_code=204)
async def remove_branch(
    branch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings:manage")),
):
    await service.delete_branch(db, current_user.clinic_id, current_user.id, branch_id)
    await db.commit()


@router.get("/operatories", response_model=list[OperatoryOut])
async def get_operatories(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings:manage")),
):
    return await service.list_operatories(db, current_user.clinic_id)


@router.post("/operatories", response_model=OperatoryOut, status_code=201)
async def post_operatory(
    payload: OperatoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings:manage")),
):
    operatory = await service.create_operatory(db, current_user.clinic_id, current_user.id, payload)
    await db.commit()
    return operatory


@router.put("/operatories/{operatory_id}", response_model=OperatoryOut)
async def put_operatory(
    operatory_id: uuid.UUID,
    payload: OperatoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings:manage")),
):
    operatory = await service.update_operatory(db, current_user.clinic_id, current_user.id, operatory_id, payload)
    await db.commit()
    return operatory


@router.delete("/operatories/{operatory_id}", status_code=204)
async def remove_operatory(
    operatory_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings:manage")),
):
    await service.delete_operatory(db, current_user.clinic_id, current_user.id, operatory_id)
    await db.commit()
