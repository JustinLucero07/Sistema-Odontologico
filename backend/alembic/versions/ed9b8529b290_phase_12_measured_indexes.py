"""phase 12 measured indexes

Revision ID: ed9b8529b290
Revises: a729cda1b80d
Create Date: 2026-09-20 17:02:04.993393

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'ed9b8529b290'
down_revision: Union[str, None] = 'a729cda1b80d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Three indexes, each added because a measurement showed it mattered.

    Measured on synthetic volume inside a rolled-back transaction:

      audit_logs      200k rows   14.9 ms -> 0.047 ms   (seq scan + sort, gone)
      stock_movements  60k rows    5.6 ms -> 0.048 ms   (seq scan + sort, gone)
      payments        150k rows   11.2 ms -> 0.52 ms    (parallel seq scan, gone)

    Three things were measured and deliberately NOT indexed:

      · `charges (clinic_id, issued_on) WHERE voided_at IS NULL` moved 6.85 ms
        to 6.66 ms — almost every charge is live, so the partial index selects
        nearly the whole table and Postgres is right to scan it.
      · The agenda's clinic_id + date range already runs in 0.05 ms at 80k
        rows on the existing `ix_appointments_starts_at`.
      · `role_permissions` and `user_roles` are read on every single request,
        but they hold tens of rows and will never hold more; a seq scan over
        40 rows beats an index lookup, and indexing them would be ritual.

    Every index costs write throughput, so the ones that earn their place are
    the ones with a number behind them."""
    op.create_index(
        "ix_audit_logs_clinic_recent",
        "audit_logs",
        ["clinic_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_stock_movements_item_recent",
        "stock_movements",
        ["item_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_payments_clinic_received",
        "payments",
        ["clinic_id", "received_on"],
    )


def downgrade() -> None:
    op.drop_index("ix_payments_clinic_received", table_name="payments")
    op.drop_index("ix_stock_movements_item_recent", table_name="stock_movements")
    op.drop_index("ix_audit_logs_clinic_recent", table_name="audit_logs")
