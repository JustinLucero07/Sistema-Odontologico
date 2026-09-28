import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.modules.expenses import service
from app.modules.expenses.constants import EXPENSE_CATEGORIES
from app.modules.expenses.schemas import (
    CashSessionRow,
    ExpenseCreate,
    ExpenseOut,
    ExpenseUpdate,
    FinanceSummary,
    PaymentRow,
)
from app.modules.reports.csv_export import render_csv
from app.modules.reports.router import _range
from app.shared.voiding import VoidRequest

router = APIRouter(prefix="/api/v1/finance", tags=["finance"])


def _csv(body: str, name: str, frm: date, to: date) -> Response:
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{name}-{frm}-{to}.csv"'},
    )


def _dec(value) -> str:
    return str(value).replace(".", ",")


@router.get("/expense-categories")
async def get_categories(current_user: CurrentUser = Depends(require_permission("payments:read"))):
    return [{"code": c, "label": l} for c, l in EXPENSE_CATEGORIES]


@router.get("/expenses", response_model=list[ExpenseOut])
async def get_expenses(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    category: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:read")),
):
    frm, to = _range(date_from, date_to)
    return await service.list_expenses(db, current_user.clinic_id, frm, to, category)


@router.get("/expenses.csv")
async def get_expenses_csv(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:read")),
):
    frm, to = _range(date_from, date_to)
    rows = await service.list_expenses(db, current_user.clinic_id, frm, to)
    body = render_csv(
        f"Egresos del {frm} al {to}",
        ["Fecha", "Categoría", "Concepto", "Proveedor", "Comprobante", "Medio", "Importe", "Estado"],
        [
            [
                r.spent_on.isoformat(), r.category_label, r.description, r.supplier_name, r.receipt_number,
                r.method_label, _dec(r.amount), "Anulado" if r.voided_at else "Vigente",
            ]
            for r in rows
        ],
    )
    return _csv(body, "egresos", frm, to)


@router.post("/expenses", response_model=ExpenseOut, status_code=201)
async def post_expense(
    payload: ExpenseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:write")),
):
    expense = await service.create_expense(db, current_user.clinic_id, current_user.id, payload)
    await db.commit()
    return expense


@router.put("/expenses/{expense_id}", response_model=ExpenseOut)
async def put_expense(
    expense_id: uuid.UUID,
    payload: ExpenseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:write")),
):
    expense = await service.update_expense(db, current_user.clinic_id, current_user.id, expense_id, payload)
    await db.commit()
    return expense


@router.post("/expenses/{expense_id}/void", response_model=ExpenseOut)
async def post_void_expense(
    expense_id: uuid.UUID,
    payload: VoidRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:write")),
):
    expense = await service.void_expense(db, current_user.clinic_id, current_user.id, expense_id, payload.reason)
    await db.commit()
    return expense


@router.get("/payments", response_model=list[PaymentRow])
async def get_payments(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    method: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:read")),
):
    frm, to = _range(date_from, date_to)
    return await service.list_payments(db, current_user.clinic_id, frm, to, method)


@router.get("/payments.csv")
async def get_payments_csv(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:read")),
):
    frm, to = _range(date_from, date_to)
    rows = await service.list_payments(db, current_user.clinic_id, frm, to)
    body = render_csv(
        f"Cobros del {frm} al {to}",
        ["Fecha", "Paciente", "Concepto", "Medio", "Referencia", "Importe", "Recibió", "Estado"],
        [
            [
                r.received_on.isoformat(), r.patient_name, r.concept or "A cuenta", r.method_label, r.reference,
                _dec(r.amount), r.received_by_name, "Anulado" if r.voided_at else "Vigente",
            ]
            for r in rows
        ],
    )
    return _csv(body, "cobros", frm, to)


@router.get("/summary", response_model=FinanceSummary)
async def get_summary(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:read")),
):
    frm, to = _range(date_from, date_to)
    return await service.summary(db, current_user.clinic_id, frm, to)


@router.get("/cash-sessions", response_model=list[CashSessionRow])
async def get_cash_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:read")),
):
    return await service.cash_sessions(db, current_user.clinic_id)
