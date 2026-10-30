import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import record_audit
from app.modules.clinics.models import Clinic
from app.modules.invoicing import crypto, mailer, ride, sri_client
from app.modules.invoicing.access_key import clave_acceso
from app.modules.invoicing.constants import (
    AMBIENTES,
    AUTORIZADA,
    CONSUMIDOR_FINAL_ID,
    CONSUMIDOR_FINAL_MAXIMO,
    CONSUMIDOR_FINAL_NOMBRE,
    DESCARTADA,
    DEVUELTA,
    EN_CURSO,
    ESPERAS_REINTENTO,
    FACTURA,
    ID_CEDULA,
    ID_CONSUMIDOR_FINAL,
    ID_RUC,
    IVA,
    NO_AUTORIZADA,
    NOTA_CREDITO,
    PENDIENTE,
    RECIBIDA,
    VIGENTES,
)
from app.modules.invoicing.identification import cedula_valida, error_identificacion, ruc_valido
from app.modules.invoicing.models import Invoice, InvoiceLine, InvoiceSequence, InvoicingSettings
from app.modules.invoicing.schemas import (
    CreditNoteCreate,
    InvoiceCreate,
    SettingsOut,
    SettingsUpdate,
)
from app.modules.invoicing.signer import firmar
from app.modules.invoicing.xml_builder import Comprobante, Emisor, Linea, construir
from app.modules.patients.service import get_patient_or_404
from app.modules.payments.models import Charge

CENTAVOS = Decimal("0.01")


def _c(v: Decimal) -> Decimal:
    return Decimal(v).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def _hoy(clinica: Clinic) -> date:
    return datetime.now(ZoneInfo(clinica.timezone or "America/Guayaquil")).date()


def _error(codigo: int, texto: str) -> HTTPException:
    return HTTPException(status_code=codigo, detail=texto)


# ---------------------------------------------------------------- Configuración


async def _config(db: AsyncSession, clinic_id: uuid.UUID) -> InvoicingSettings:
    fila = (await db.execute(select(InvoicingSettings).where(InvoicingSettings.clinic_id == clinic_id))).scalar_one_or_none()
    if fila is None:
        fila = InvoicingSettings(clinic_id=clinic_id, environment="1", send_email=True)
        db.add(fila)
        await db.flush()
    return fila


async def _clinica(db: AsyncSession, clinic_id: uuid.UUID) -> Clinic:
    return (await db.execute(select(Clinic).where(Clinic.id == clinic_id))).scalar_one()


def _faltantes(clinica: Clinic, conf: InvoicingSettings) -> list[str]:
    falta = []
    ruc = (clinica.tax_id or "").strip()
    if not ruc:
        falta.append("El RUC de la consulta (Datos de la consulta).")
    elif not ruc_valido(ruc):
        falta.append("El RUC de la consulta no es válido: deben ser 13 dígitos.")
    if not (clinica.legal_name or clinica.name):
        falta.append("La razón social (Datos de la consulta).")
    if not (clinica.address or "").strip():
        falta.append("La dirección de la matriz (Datos de la consulta).")
    if not conf.certificate:
        falta.append("La firma electrónica (.p12) y su clave.")
    elif conf.certificate_valid_until and conf.certificate_valid_until < datetime.now(timezone.utc):
        falta.append("La firma electrónica está vencida: suba la renovada.")
    return falta


async def _siguiente(db: AsyncSession, clinic_id: uuid.UUID, estab: str, punto: str, tipo: str, bloquear: bool) -> InvoiceSequence:
    consulta = select(InvoiceSequence).where(
        InvoiceSequence.clinic_id == clinic_id,
        InvoiceSequence.establishment == estab,
        InvoiceSequence.emission_point == punto,
        InvoiceSequence.doc_type == tipo,
    )
    if bloquear:
        consulta = consulta.with_for_update()
    fila = (await db.execute(consulta)).scalar_one_or_none()
    if fila is None:
        fila = InvoiceSequence(clinic_id=clinic_id, establishment=estab, emission_point=punto, doc_type=tipo, next_value=1)
        db.add(fila)
        await db.flush()
        if bloquear:
            fila = (await db.execute(consulta)).scalar_one()
    return fila


async def get_settings(db: AsyncSession, clinic_id: uuid.UUID) -> SettingsOut:
    conf = await _config(db, clinic_id)
    clinica = await _clinica(db, clinic_id)
    secuencia = await _siguiente(db, clinic_id, clinica.sri_establishment, clinica.sri_emission_point, FACTURA, False)
    vence = conf.certificate_valid_until
    return SettingsOut(
        environment=conf.environment,
        send_email=conf.send_email,
        retention_agent=conf.retention_agent,
        has_certificate=conf.certificate is not None,
        certificate_subject=conf.certificate_subject,
        certificate_valid_until=vence,
        certificate_expired=bool(vence and vence < datetime.now(timezone.utc)),
        email_configured=mailer.configurado(),
        next_invoice_number=secuencia.next_value,
        establishment=clinica.sri_establishment,
        emission_point=clinica.sri_emission_point,
        missing=_faltantes(clinica, conf),
    )


async def update_settings(db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, datos: SettingsUpdate) -> SettingsOut:
    conf = await _config(db, clinic_id)
    clinica = await _clinica(db, clinic_id)
    cambios = datos.model_dump(exclude_unset=True)
    if "environment" in cambios and cambios["environment"]:
        conf.environment = cambios["environment"]
    if "send_email" in cambios and cambios["send_email"] is not None:
        conf.send_email = cambios["send_email"]
    if "retention_agent" in cambios:
        conf.retention_agent = (cambios["retention_agent"] or "").strip() or None
    if cambios.get("next_invoice_number"):
        secuencia = await _siguiente(db, clinic_id, clinica.sri_establishment, clinica.sri_emission_point, FACTURA, True)
        usado = (
            await db.execute(
                select(func.max(Invoice.sequential)).where(
                    Invoice.clinic_id == clinic_id,
                    Invoice.doc_type == FACTURA,
                    Invoice.establishment == clinica.sri_establishment,
                    Invoice.emission_point == clinica.sri_emission_point,
                )
            )
        ).scalar_one()
        if usado and cambios["next_invoice_number"] <= usado:
            raise _error(409, f"Ya se emitió la factura número {usado}: el siguiente debe ser mayor.")
        secuencia.next_value = cambios["next_invoice_number"]
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="update", entity_type="invoicing_settings",
        entity_id=str(conf.id), after={k: v for k, v in cambios.items()},
    )
    return await get_settings(db, clinic_id)


async def upload_certificate(db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, contenido: bytes, clave: str) -> SettingsOut:
    if len(contenido) > 100_000:
        raise _error(422, "El archivo es demasiado grande para ser una firma .p12.")
    try:
        _, certificado = crypto.abrir_p12(contenido, clave)
    except crypto.FirmaInvalida as e:
        raise _error(422, str(e)) from e
    if not crypto.vigente(certificado):
        raise _error(422, f"La firma venció el {certificado.not_valid_after_utc:%d/%m/%Y}. Suba la renovada.")
    conf = await _config(db, clinic_id)
    conf.certificate = crypto.cifrar(contenido)
    conf.certificate_password = crypto.cifrar(clave.encode())
    conf.certificate_subject = certificado.subject.rfc4514_string()[:300]
    conf.certificate_serial = str(certificado.serial_number)[:80]
    conf.certificate_valid_until = certificado.not_valid_after_utc
    conf.certificate_uploaded_at = datetime.now(timezone.utc)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="upload_certificate", entity_type="invoicing_settings",
        entity_id=str(conf.id), after={"subject": conf.certificate_subject, "valid_until": conf.certificate_valid_until},
    )
    return await get_settings(db, clinic_id)


async def delete_certificate(db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID) -> SettingsOut:
    conf = await _config(db, clinic_id)
    conf.certificate = None
    conf.certificate_password = None
    conf.certificate_subject = None
    conf.certificate_serial = None
    conf.certificate_valid_until = None
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="delete_certificate", entity_type="invoicing_settings", entity_id=str(conf.id),
    )
    return await get_settings(db, clinic_id)


# ---------------------------------------------------------------- Consultas


def _cargar():
    return selectinload(Invoice.lines)


async def get_invoice_or_404(db: AsyncSession, clinic_id: uuid.UUID, invoice_id: uuid.UUID) -> Invoice:
    factura = (
        await db.execute(select(Invoice).options(_cargar()).where(Invoice.id == invoice_id, Invoice.clinic_id == clinic_id))
    ).scalar_one_or_none()
    if factura is None:
        raise _error(404, "Comprobante no encontrado")
    return factura


async def acreditado(db: AsyncSession, factura: Invoice) -> Decimal:
    """Total de las notas de crédito vigentes emitidas sobre una factura."""
    total = (
        await db.execute(
            select(func.coalesce(func.sum(Invoice.total), 0)).where(
                Invoice.modified_invoice_id == factura.id, Invoice.status.in_(VIGENTES)
            )
        )
    ).scalar_one()
    return _c(total)


async def list_invoices(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    *,
    estado: str | None = None,
    tipo: str | None = None,
    paciente: uuid.UUID | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    texto: str | None = None,
    limit: int = 200,
) -> list[Invoice]:
    q = select(Invoice).options(_cargar()).where(Invoice.clinic_id == clinic_id)
    if estado:
        q = q.where(Invoice.status == estado)
    if tipo:
        q = q.where(Invoice.doc_type == tipo)
    if paciente:
        q = q.where(Invoice.patient_id == paciente)
    if desde:
        q = q.where(Invoice.issue_date >= desde)
    if hasta:
        q = q.where(Invoice.issue_date <= hasta)
    if texto:
        t = f"%{texto.strip()}%"
        q = q.where(Invoice.buyer_name.ilike(t) | Invoice.buyer_id.ilike(t) | Invoice.access_key.ilike(t))
    q = q.order_by(Invoice.created_at.desc()).limit(min(max(limit, 1), 1000))
    return list((await db.execute(q)).scalars().all())


async def _cargos_facturados(db: AsyncSession, cargos: list[uuid.UUID]) -> set[uuid.UUID]:
    if not cargos:
        return set()
    filas = await db.execute(
        select(InvoiceLine.charge_id)
        .join(Invoice, Invoice.id == InvoiceLine.invoice_id)
        .where(InvoiceLine.charge_id.in_(cargos), Invoice.doc_type == FACTURA, Invoice.status.in_(VIGENTES))
    )
    return {fila[0] for fila in filas.all()}


async def invoiceable_charges(db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID) -> list[Charge]:
    await get_patient_or_404(db, clinic_id, patient_id)
    cargos = list(
        (
            await db.execute(
                select(Charge)
                .where(Charge.clinic_id == clinic_id, Charge.patient_id == patient_id, Charge.voided_at.is_(None))
                .order_by(Charge.issued_on.desc())
            )
        )
        .scalars()
        .all()
    )
    ya = await _cargos_facturados(db, [c.id for c in cargos])
    return [c for c in cargos if c.id not in ya]


async def charge_is_invoiced(db: AsyncSession, charge_id: uuid.UUID) -> bool:
    """Para no anular un cargo que figura en una factura vigente: primero va la
    nota de crédito."""
    return bool(await _cargos_facturados(db, [charge_id]))


# ---------------------------------------------------------------- Emisión


def _linea(posicion: int, codigo: str, descripcion: str, cantidad: Decimal, precio: Decimal, incluye_iva: bool, descuento: Decimal, codigo_iva: str, cargo: uuid.UUID | None) -> InvoiceLine:
    tarifa = IVA[codigo_iva][1]
    if incluye_iva and tarifa:
        # «Cuesta 115 con IVA» → base 100 + IVA 15. Se separa sobre el total
        # de la línea para no arrastrar redondeos por unidad.
        bruto = _c(cantidad * precio) - _c(descuento)
        base = _c(bruto / (1 + tarifa / 100))
        unitario = (base + _c(descuento)) / cantidad
    else:
        unitario = precio
        base = _c(cantidad * precio) - _c(descuento)
    if base < 0:
        raise _error(422, f"El descuento de «{descripcion}» es mayor que su valor.")
    return InvoiceLine(
        charge_id=cargo,
        position=posicion,
        code=(codigo or f"L{posicion}")[:25],
        description=descripcion[:300],
        quantity=cantidad,
        unit_price=Decimal(unitario).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP),
        discount=_c(descuento),
        subtotal=base,
        vat_code=codigo_iva,
        vat_rate=tarifa,
        vat=_c(base * tarifa / 100),
    )


def _comprador_de(paciente) -> tuple[str, str, str]:
    cedula = (paciente.national_id or "").strip()
    if len(cedula) == 10 and cedula_valida(cedula):
        return ID_CEDULA, cedula, f"{paciente.first_name} {paciente.last_name}"
    if len(cedula) == 13 and ruc_valido(cedula):
        return ID_RUC, cedula, f"{paciente.first_name} {paciente.last_name}"
    return ID_CONSUMIDOR_FINAL, CONSUMIDOR_FINAL_ID, CONSUMIDOR_FINAL_NOMBRE


async def create_invoice(db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, datos: InvoiceCreate) -> Invoice:
    clinica = await _clinica(db, clinic_id)
    conf = await _config(db, clinic_id)
    falta = _faltantes(clinica, conf)
    if falta:
        raise _error(409, "Antes de facturar complete: " + " ".join(falta))

    paciente = await get_patient_or_404(db, clinic_id, datos.patient_id) if datos.patient_id else None

    # Comprador: el indicado; si no, el paciente; si no, consumidor final.
    if datos.buyer:
        b = datos.buyer
        tipo_id, numero, nombre = b.id_type, b.id_number.strip(), b.name.strip()
        correo, direccion, telefono = b.email, b.address, b.phone
        if tipo_id == ID_CONSUMIDOR_FINAL:
            numero, nombre = CONSUMIDOR_FINAL_ID, CONSUMIDOR_FINAL_NOMBRE
    elif paciente:
        tipo_id, numero, nombre = _comprador_de(paciente)
        correo, direccion, telefono = paciente.email, paciente.address, paciente.phone or paciente.whatsapp
    else:
        tipo_id, numero, nombre = ID_CONSUMIDOR_FINAL, CONSUMIDOR_FINAL_ID, CONSUMIDOR_FINAL_NOMBRE
        correo = direccion = telefono = None
    problema = error_identificacion(tipo_id, numero)
    if problema:
        raise _error(422, problema)

    # Líneas.
    ids_cargos = [i.charge_id for i in datos.items if i.charge_id]
    if len(ids_cargos) != len(set(ids_cargos)):
        raise _error(422, "Un mismo cargo aparece dos veces.")
    cargos: dict[uuid.UUID, Charge] = {}
    if ids_cargos:
        if paciente is None:
            raise _error(422, "Para facturar cargos de la cuenta indique el paciente.")
        filas = (await db.execute(select(Charge).where(Charge.id.in_(ids_cargos), Charge.clinic_id == clinic_id))).scalars().all()
        cargos = {c.id: c for c in filas}
        for cid in ids_cargos:
            c = cargos.get(cid)
            if c is None or c.patient_id != paciente.id:
                raise _error(404, "Cargo no encontrado en la cuenta de este paciente.")
            if c.voided_at is not None:
                raise _error(409, f"El cargo «{c.description}» está anulado.")
        ya = await _cargos_facturados(db, ids_cargos)
        if ya:
            raise _error(409, "Uno de los cargos ya está en otra factura vigente.")

    lineas: list[InvoiceLine] = []
    for i, item in enumerate(datos.items, start=1):
        if item.charge_id:
            c = cargos[item.charge_id]
            lineas.append(_linea(i, f"C{i}", c.description, Decimal(1), Decimal(c.amount), True, item.discount, item.vat_code, c.id))
        else:
            if not (item.description or "").strip() or item.unit_price is None:
                raise _error(422, f"La línea {i} necesita descripción y precio.")
            lineas.append(
                _linea(i, item.code or f"S{i}", item.description.strip(), item.quantity, item.unit_price, item.price_includes_vat, item.discount, item.vat_code, None)
            )

    subtotal = sum((ln.subtotal for ln in lineas), Decimal(0))
    descuento = sum((ln.discount for ln in lineas), Decimal(0))
    iva = sum((ln.vat for ln in lineas), Decimal(0))
    total = _c(subtotal + iva)
    if total <= 0:
        raise _error(422, "El total de la factura debe ser mayor que cero.")
    if tipo_id == ID_CONSUMIDOR_FINAL and total > CONSUMIDOR_FINAL_MAXIMO:
        raise _error(
            422, f"A consumidor final solo se puede facturar hasta ${CONSUMIDOR_FINAL_MAXIMO}. Indique la cédula o RUC del comprador."
        )

    factura = await _numerar(db, clinica, conf, FACTURA)
    factura.patient_id = paciente.id if paciente else None
    factura.buyer_id_type, factura.buyer_id, factura.buyer_name = tipo_id, numero, nombre[:300]
    factura.buyer_email, factura.buyer_address, factura.buyer_phone = correo, direccion, telefono
    factura.payment_method = datos.payment_method
    factura.subtotal, factura.discount, factura.vat, factura.total = _c(subtotal), _c(descuento), _c(iva), total
    factura.notes = (datos.notes or "").strip() or None
    factura.created_by_id = actor_id
    factura.lines = lineas
    db.add(factura)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="create", entity_type="invoice", entity_id=str(factura.id),
        after={"number": factura.number, "total": factura.total, "buyer": factura.buyer_id},
    )
    return factura


async def _numerar(db: AsyncSession, clinica: Clinic, conf: InvoicingSettings, tipo: str) -> Invoice:
    """Reserva el número con bloqueo de fila y arma la clave de acceso."""
    secuencia = await _siguiente(db, clinica.id, clinica.sri_establishment, clinica.sri_emission_point, tipo, True)
    numero = secuencia.next_value
    secuencia.next_value = numero + 1
    hoy = _hoy(clinica)
    return Invoice(
        clinic_id=clinica.id,
        doc_type=tipo,
        environment=conf.environment,
        establishment=clinica.sri_establishment,
        emission_point=clinica.sri_emission_point,
        sequential=numero,
        access_key=clave_acceso(
            fecha=hoy, tipo=tipo, ruc=clinica.tax_id.strip(), ambiente=conf.environment,
            establecimiento=clinica.sri_establishment, punto_emision=clinica.sri_emission_point, secuencial=numero,
        ),
        issue_date=hoy,
        status=PENDIENTE,
        sri_messages=[],
        attempts=0,
        next_attempt_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )


async def create_credit_note(db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, invoice_id: uuid.UUID, datos: CreditNoteCreate) -> Invoice:
    original = await get_invoice_or_404(db, clinic_id, invoice_id)
    if original.doc_type != FACTURA or original.status != AUTORIZADA:
        raise _error(409, "Solo se emite nota de crédito sobre una factura autorizada.")
    clinica = await _clinica(db, clinic_id)
    conf = await _config(db, clinic_id)
    falta = _faltantes(clinica, conf)
    if falta:
        raise _error(409, "Antes de emitir complete: " + " ".join(falta))

    disponible = _c(original.total - await acreditado(db, original))
    if disponible <= 0:
        raise _error(409, "Esta factura ya fue anulada por completo con notas de crédito.")

    if datos.amount is None or _c(datos.amount) == disponible and disponible == original.total:
        if disponible != original.total:
            raise _error(409, f"Ya hay notas de crédito sobre esta factura: indique un monto (hasta ${disponible}).")
        lineas = [
            InvoiceLine(
                charge_id=ln.charge_id, position=ln.position, code=ln.code, description=ln.description,
                quantity=ln.quantity, unit_price=ln.unit_price, discount=ln.discount, subtotal=ln.subtotal,
                vat_code=ln.vat_code, vat_rate=ln.vat_rate, vat=ln.vat,
            )
            for ln in original.lines
        ]
    else:
        monto = _c(datos.amount)
        if monto > disponible:
            raise _error(422, f"El monto supera lo que queda por acreditar (${disponible}).")
        codigos = {ln.vat_code for ln in original.lines}
        if len(codigos) > 1:
            raise _error(422, "La factura mezcla tarifas de IVA: para una nota parcial anule la factura completa y emita una nueva.")
        lineas = [_linea(1, "NC1", f"Devolución / ajuste: {datos.reason.strip()}", Decimal(1), monto, True, Decimal(0), codigos.pop(), None)]

    nota = await _numerar(db, clinica, conf, NOTA_CREDITO)
    nota.patient_id = original.patient_id
    nota.modified_invoice_id = original.id
    nota.reason = datos.reason.strip()
    nota.buyer_id_type, nota.buyer_id, nota.buyer_name = original.buyer_id_type, original.buyer_id, original.buyer_name
    nota.buyer_email, nota.buyer_address, nota.buyer_phone = original.buyer_email, original.buyer_address, original.buyer_phone
    nota.payment_method = original.payment_method
    subtotal = sum((ln.subtotal for ln in lineas), Decimal(0))
    iva = sum((ln.vat for ln in lineas), Decimal(0))
    nota.subtotal, nota.discount, nota.vat, nota.total = _c(subtotal), _c(sum((ln.discount for ln in lineas), Decimal(0))), _c(iva), _c(subtotal + iva)
    nota.created_by_id = actor_id
    nota.lines = lineas
    db.add(nota)
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="credit_note", entity_type="invoice", entity_id=str(nota.id),
        after={"number": nota.number, "modifies": original.number, "total": nota.total, "reason": nota.reason},
    )
    return nota


# ---------------------------------------------------------------- Envío al SRI


def _emisor(clinica: Clinic, conf: InvoicingSettings) -> Emisor:
    return Emisor(
        ruc=clinica.tax_id.strip(),
        razon_social=clinica.legal_name or clinica.name,
        nombre_comercial=clinica.name if clinica.legal_name and clinica.legal_name != clinica.name else None,
        direccion_matriz=clinica.address or "",
        direccion_establecimiento=clinica.address or "",
        obligado_contabilidad=clinica.keeps_accounting,
        contribuyente_especial=clinica.special_taxpayer,
        regimen=clinica.tax_regime,
        agente_retencion=conf.retention_agent,
    )


def _comprobante(factura: Invoice, original: Invoice | None) -> Comprobante:
    adicional = {"Correo": factura.buyer_email or "", "Teléfono": factura.buyer_phone or "", "Observación": factura.notes or ""}
    return Comprobante(
        tipo=factura.doc_type,
        ambiente=factura.environment,
        clave_acceso=factura.access_key,
        establecimiento=factura.establishment,
        punto_emision=factura.emission_point,
        secuencial=factura.sequential,
        fecha_emision=f"{factura.issue_date:%d/%m/%Y}",
        tipo_id_comprador=factura.buyer_id_type,
        id_comprador=factura.buyer_id,
        razon_social_comprador=factura.buyer_name,
        direccion_comprador=factura.buyer_address,
        subtotal=factura.subtotal,
        descuento=factura.discount,
        iva=factura.vat,
        total=factura.total,
        lineas=[
            Linea(ln.code, ln.description, ln.quantity, ln.unit_price, ln.discount, ln.subtotal, ln.vat_code, ln.vat_rate, ln.vat)
            for ln in factura.lines
        ],
        forma_pago=factura.payment_method,
        info_adicional=adicional,
        doc_modificado_numero=original.number if original else None,
        doc_modificado_fecha=f"{original.issue_date:%d/%m/%Y}" if original else None,
        motivo=factura.reason,
    )


def _mensajes(lista) -> list[dict]:
    return [m.como_dict() for m in lista]


def _reprogramar(factura: Invoice, error: str) -> None:
    factura.attempts += 1
    espera = ESPERAS_REINTENTO[min(factura.attempts - 1, len(ESPERAS_REINTENTO) - 1)]
    factura.next_attempt_at = datetime.now(timezone.utc) + timedelta(minutes=espera)
    factura.last_error = error


async def firmar_xml(db: AsyncSession, factura: Invoice) -> bytes:
    clinica = await _clinica(db, factura.clinic_id)
    conf = await _config(db, factura.clinic_id)
    if not conf.certificate or not conf.certificate_password:
        raise crypto.FirmaInvalida("Falta la firma electrónica.")
    llave, certificado = crypto.abrir_p12(crypto.descifrar(conf.certificate), crypto.descifrar(conf.certificate_password).decode())
    if not crypto.vigente(certificado):
        raise crypto.FirmaInvalida("La firma electrónica está vencida.")
    original = None
    if factura.modified_invoice_id:
        original = (await db.execute(select(Invoice).where(Invoice.id == factura.modified_invoice_id))).scalar_one()
    return firmar(construir(_emisor(clinica, conf), _comprobante(factura, original)), llave, certificado)


async def process(db: AsyncSession, factura: Invoice) -> Invoice:
    """Avanza un comprobante un paso con el SRI: firma y envía si está
    pendiente, y consulta la autorización si ya fue recibido. Nunca lanza por
    fallas del SRI: las deja anotadas y reprograma el reintento."""
    if factura.status not in EN_CURSO:
        return factura
    try:
        if factura.status == PENDIENTE:
            try:
                xml = await firmar_xml(db, factura)
            except (crypto.FirmaInvalida, ValueError) as e:
                factura.status = DEVUELTA
                factura.sri_messages = [{"identificador": "FIRMA", "mensaje": str(e), "informacion": "", "tipo": "ERROR"}]
                factura.next_attempt_at = None
                return factura
            errores = sri_client.errores_de_esquema(xml, factura.doc_type)
            if errores:
                factura.status = DEVUELTA
                factura.sri_messages = [{"identificador": "XSD", "mensaje": "El comprobante no cumple el formato del SRI.", "informacion": " | ".join(errores), "tipo": "ERROR"}]
                factura.next_attempt_at = None
                return factura
            factura.signed_xml = xml.decode()
            recepcion = await sri_client.enviar(xml, factura.environment)
            factura.sri_messages = _mensajes(recepcion.mensajes)
            if recepcion.estado == "RECIBIDA" or recepcion.ya_registrada:
                factura.status = RECIBIDA
            else:
                factura.status = DEVUELTA
                factura.next_attempt_at = None
                return factura

        autorizacion = await sri_client.consultar(factura.access_key, factura.environment)
        if autorizacion.estado == "AUTORIZADO":
            factura.status = AUTORIZADA
            factura.authorized_at = autorizacion.fecha or datetime.now(timezone.utc)
            comprobante = autorizacion.comprobante or factura.signed_xml or ""
            factura.authorized_xml = (
                '<?xml version="1.0" encoding="UTF-8"?>\n<autorizacion>'
                f"<estado>AUTORIZADO</estado><numeroAutorizacion>{escape(autorizacion.numero or factura.access_key)}</numeroAutorizacion>"
                f"<fechaAutorizacion>{factura.authorized_at.isoformat()}</fechaAutorizacion>"
                f"<ambiente>{AMBIENTES[factura.environment].upper()}</ambiente>"
                f"<comprobante><![CDATA[{comprobante}]]></comprobante></autorizacion>"
            )
            factura.sri_messages = _mensajes(autorizacion.mensajes)
            factura.next_attempt_at = None
            factura.last_error = None
        elif autorizacion.estado == "NO AUTORIZADO":
            factura.status = NO_AUTORIZADA
            factura.sri_messages = _mensajes(autorizacion.mensajes)
            factura.next_attempt_at = None
        else:
            # Aún en proceso: se vuelve a consultar en un momento.
            _reprogramar(factura, "El SRI aún no responde la autorización.")
    except sri_client.SriNoDisponible as e:
        _reprogramar(factura, str(e))
    return factura


async def process_and_notify(db: AsyncSession, factura: Invoice) -> Invoice:
    await process(db, factura)
    if factura.status == AUTORIZADA and factura.emailed_at is None and factura.buyer_email and mailer.configurado():
        conf = await _config(db, factura.clinic_id)
        if conf.send_email:
            try:
                await send_email(db, factura, None)
            except Exception as e:  # el correo no debe deshacer la autorización
                factura.last_error = f"Autorizada, pero no se pudo enviar el correo: {e}"
    return factura


async def process_due(db: AsyncSession) -> int:
    """Lo que corre el proceso en segundo plano: retoma todo lo pendiente, de
    todas las consultas."""
    ahora = datetime.now(timezone.utc)
    pendientes = (
        await db.execute(
            select(Invoice).options(_cargar())
            .where(Invoice.status.in_(EN_CURSO), Invoice.next_attempt_at.is_not(None), Invoice.next_attempt_at <= ahora)
            .order_by(Invoice.next_attempt_at)
            .limit(100)
        )
    ).scalars().all()
    for factura in pendientes:
        await process_and_notify(db, factura)
        await db.commit()
    return len(pendientes)


async def retry(db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, invoice_id: uuid.UUID) -> Invoice:
    factura = await get_invoice_or_404(db, clinic_id, invoice_id)
    if factura.status in (AUTORIZADA, DESCARTADA):
        raise _error(409, "Este comprobante ya no se puede reenviar.")
    if factura.status in (DEVUELTA, NO_AUTORIZADA):
        # Se vuelve a firmar con los datos actuales (p. ej. tras corregir el RUC
        # o subir la firma) y con la misma clave de acceso.
        factura.status = PENDIENTE
        factura.attempts = 0
    factura.next_attempt_at = datetime.now(timezone.utc)
    await record_audit(db, clinic_id=clinic_id, user_id=actor_id, action="retry", entity_type="invoice", entity_id=str(factura.id))
    return await process_and_notify(db, factura)


async def discard(db: AsyncSession, clinic_id: uuid.UUID, actor_id: uuid.UUID, invoice_id: uuid.UUID, motivo: str) -> Invoice:
    factura = await get_invoice_or_404(db, clinic_id, invoice_id)
    if factura.status not in (DEVUELTA, NO_AUTORIZADA, PENDIENTE):
        raise _error(
            409,
            "Una factura autorizada se anula con nota de crédito." if factura.status == AUTORIZADA else "Este comprobante no se puede descartar ahora.",
        )
    if factura.status == PENDIENTE and factura.signed_xml:
        raise _error(409, "Ya se envió al SRI: espere su respuesta antes de descartarlo.")
    factura.status = DESCARTADA
    factura.discarded_at = datetime.now(timezone.utc)
    factura.discard_reason = motivo.strip()
    factura.next_attempt_at = None
    await db.flush()
    await record_audit(
        db, clinic_id=clinic_id, user_id=actor_id, action="discard", entity_type="invoice", entity_id=str(factura.id),
        after={"reason": factura.discard_reason},
    )
    return factura


# ---------------------------------------------------------------- PDF, XML, correo


async def pdf(db: AsyncSession, factura: Invoice) -> bytes:
    clinica = await _clinica(db, factura.clinic_id)
    original = None
    if factura.modified_invoice_id:
        original = await get_invoice_or_404(db, factura.clinic_id, factura.modified_invoice_id)
    return ride.generar(factura, clinica, original)


def nombre_archivo(factura: Invoice, extension: str) -> str:
    tipo = "factura" if factura.doc_type == FACTURA else "nota-credito"
    return f"{tipo}-{factura.number}.{extension}"


async def send_email(db: AsyncSession, factura: Invoice, destino: str | None) -> Invoice:
    if factura.status != AUTORIZADA:
        raise _error(409, "Solo se envía una vez autorizada por el SRI.")
    if not mailer.configurado():
        raise _error(409, "El correo saliente no está configurado en el servidor (SMTP).")
    para = destino or factura.buyer_email
    if not para:
        raise _error(422, "El comprador no tiene correo: indique uno.")
    clinica = await _clinica(db, factura.clinic_id)
    tipo = "Factura" if factura.doc_type == FACTURA else "Nota de crédito"
    await mailer.enviar(
        para,
        f"{tipo} {factura.number} — {clinica.name}",
        f"Estimado/a {factura.buyer_name}:\n\nAdjuntamos su {tipo.lower()} electrónica {factura.number} "
        f"por ${factura.total}, autorizada por el SRI.\n\n{clinica.name}",
        [
            (nombre_archivo(factura, "pdf"), await pdf(db, factura), "application/pdf"),
            (nombre_archivo(factura, "xml"), (factura.authorized_xml or "").encode(), "application/xml"),
        ],
    )
    factura.emailed_at = datetime.now(timezone.utc)
    await db.flush()
    return factura
