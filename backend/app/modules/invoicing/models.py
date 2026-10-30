import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.shared.mixins import TenantMixin, UUIDPKMixin


class InvoicingSettings(UUIDPKMixin, TenantMixin, Base):
    """Configuración de facturación electrónica de una consulta.

    La firma (.p12) y su clave se guardan CIFRADAS con una llave que vive en
    el servidor (app.modules.invoicing.crypto), nunca en claro: quien robe un
    respaldo de la base no puede facturar a nombre de la consulta."""

    __tablename__ = "invoicing_settings"
    __table_args__ = (UniqueConstraint("clinic_id", name="uq_invoicing_settings_clinic"),)

    environment: Mapped[str] = mapped_column(String(1), default="1", server_default="1")
    certificate: Mapped[bytes | None] = mapped_column(LargeBinary)
    certificate_password: Mapped[bytes | None] = mapped_column(LargeBinary)
    certificate_subject: Mapped[str | None] = mapped_column(String(300))
    certificate_serial: Mapped[str | None] = mapped_column(String(80))
    certificate_valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    certificate_uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retention_agent: Mapped[str | None] = mapped_column(String(20))
    # Envía al paciente el PDF y el XML por correo al autorizarse.
    send_email: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class InvoiceSequence(UUIDPKMixin, TenantMixin, Base):
    """Siguiente número por establecimiento, punto de emisión y tipo. Se lee
    con bloqueo de fila: dos personas que facturan a la vez nunca obtienen el
    mismo número."""

    __tablename__ = "invoice_sequences"
    __table_args__ = (
        UniqueConstraint(
            "clinic_id", "establishment", "emission_point", "doc_type", name="uq_invoice_sequence"
        ),
    )

    establishment: Mapped[str] = mapped_column(String(3), nullable=False)
    emission_point: Mapped[str] = mapped_column(String(3), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(2), nullable=False)
    next_value: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class Invoice(UUIDPKMixin, TenantMixin, Base):
    """Factura o nota de crédito electrónica.

    Lo que se emitió no se borra ni se edita: una factura autorizada se corrige
    con una nota de crédito, y una rechazada por el SRI se descarta con su
    motivo. Los datos del comprador y del emisor se copian al emitir, para que
    el comprobante no cambie si después cambia la ficha del paciente."""

    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("clinic_id", "doc_type", "establishment", "emission_point", "sequential", name="uq_invoice_number"),
        UniqueConstraint("access_key", name="uq_invoice_access_key"),
    )

    doc_type: Mapped[str] = mapped_column(String(2), nullable=False)
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", name="fk_invoices_patient"), index=True
    )
    # Nota de crédito: la factura que modifica.
    modified_invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id", name="fk_invoices_modified"), index=True
    )
    reason: Mapped[str | None] = mapped_column(String(300))

    environment: Mapped[str] = mapped_column(String(1), nullable=False)
    establishment: Mapped[str] = mapped_column(String(3), nullable=False)
    emission_point: Mapped[str] = mapped_column(String(3), nullable=False)
    sequential: Mapped[int] = mapped_column(Integer, nullable=False)
    access_key: Mapped[str] = mapped_column(String(49), nullable=False)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)

    buyer_id_type: Mapped[str] = mapped_column(String(2), nullable=False)
    buyer_id: Mapped[str] = mapped_column(String(20), nullable=False)
    buyer_name: Mapped[str] = mapped_column(String(300), nullable=False)
    buyer_email: Mapped[str | None] = mapped_column(String(255))
    buyer_address: Mapped[str | None] = mapped_column(String(300))
    buyer_phone: Mapped[str | None] = mapped_column(String(50))

    payment_method: Mapped[str] = mapped_column(String(2), nullable=False, default="01")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    vat: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(300))

    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    sri_messages: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    signed_xml: Mapped[str | None] = mapped_column(Text)
    authorized_xml: Mapped[str | None] = mapped_column(Text)
    authorized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_error: Mapped[str | None] = mapped_column(Text)
    emailed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    discarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    discard_reason: Mapped[str | None] = mapped_column(Text)

    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", name="fk_invoices_created_by")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    lines: Mapped[list["InvoiceLine"]] = relationship(
        back_populates="invoice", order_by="InvoiceLine.position", cascade="all, delete-orphan"
    )

    @property
    def number(self) -> str:
        return f"{self.establishment}-{self.emission_point}-{self.sequential:09d}"


class InvoiceLine(UUIDPKMixin, Base):
    __tablename__ = "invoice_lines"

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id", name="fk_invoice_lines_invoice", ondelete="CASCADE"), nullable=False, index=True
    )
    # El cargo de la cuenta del paciente que esta línea factura (si viene de uno).
    charge_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("charges.id", name="fk_invoice_lines_charge"), index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    code: Mapped[str] = mapped_column(String(25), nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    vat_code: Mapped[str] = mapped_column(String(2), nullable=False)
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    vat: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    invoice: Mapped["Invoice"] = relationship(back_populates="lines")
