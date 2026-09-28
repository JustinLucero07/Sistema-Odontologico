"""Cálculo del calendario de cuotas.

Sistema francés (cuota fija), el habitual en créditos de consumo: cada cuota
paga el interés del saldo y el resto amortiza capital. Sin interés, el capital
se reparte en partes iguales. Todo en Decimal y a centavos; el redondeo se
ajusta en la última cuota para que el total cierre exacto."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

CENTS = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENTS, rounding=ROUND_HALF_UP)


@dataclass
class Row:
    number: int
    due_on: date
    principal: Decimal
    interest: Decimal

    @property
    def amount(self) -> Decimal:
        return self.principal + self.interest


def period_rate(monthly_rate_percent: Decimal, every_days: int) -> Decimal:
    """Tasa del periodo a partir de la mensual, proporcional a los días."""
    return (Decimal(monthly_rate_percent) / Decimal(100)) * Decimal(every_days) / Decimal(30)


def schedule(
    principal: Decimal,
    count: int,
    monthly_rate_percent: Decimal,
    every_days: int,
    first_due_on: date,
    start_number: int = 1,
) -> list[Row]:
    principal = _money(Decimal(principal))
    r = period_rate(monthly_rate_percent, every_days)
    rows: list[Row] = []
    balance = principal
    if r == 0:
        base = _money(principal / count)
        for i in range(count):
            part = base if i < count - 1 else principal - base * (count - 1)
            rows.append(Row(start_number + i, first_due_on + timedelta(days=every_days * i), _money(part), Decimal("0.00")))
        return rows

    payment = _money(principal * r / (1 - (1 + r) ** -count))
    for i in range(count):
        interest = _money(balance * r)
        part = payment - interest
        if i == count - 1:
            part = balance  # la última cierra el saldo exacto
        part = _money(part)
        balance = _money(balance - part)
        rows.append(Row(start_number + i, first_due_on + timedelta(days=every_days * i), part, interest))
    return rows
