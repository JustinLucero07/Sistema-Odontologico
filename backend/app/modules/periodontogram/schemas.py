import uuid
from datetime import datetime

from pydantic import BaseModel, Field, computed_field, field_validator

from app.modules.odontogram.constants import VALID_FDI_NUMBERS
from app.modules.periodontogram.constants import (
    MAX_FURCATION,
    MAX_MOBILITY,
    MAX_PROBING_DEPTH_MM,
    MAX_RECESSION_MM,
    MIN_RECESSION_MM,
    PERIODONTAL_SITE_CODES,
)


def _validate_fdi(value: str) -> str:
    if value not in VALID_FDI_NUMBERS:
        raise ValueError(f"Número FDI inválido: {value}")
    return value


class MeasurementIn(BaseModel):
    fdi_number: str
    site: str
    probing_depth: int | None = None
    recession: int | None = None
    bleeding: bool = False
    suppuration: bool = False
    plaque: bool = False

    _fdi = field_validator("fdi_number")(_validate_fdi)

    @field_validator("site")
    @classmethod
    def validate_site(cls, value: str) -> str:
        if value not in PERIODONTAL_SITE_CODES:
            raise ValueError(f"Sitio periodontal inválido: {value}")
        return value

    @field_validator("probing_depth")
    @classmethod
    def validate_depth(cls, value: int | None) -> int | None:
        if value is not None and not 0 <= value <= MAX_PROBING_DEPTH_MM:
            raise ValueError(f"Profundidad de sondaje fuera de rango (0–{MAX_PROBING_DEPTH_MM} mm)")
        return value

    @field_validator("recession")
    @classmethod
    def validate_recession(cls, value: int | None) -> int | None:
        if value is not None and not MIN_RECESSION_MM <= value <= MAX_RECESSION_MM:
            raise ValueError(
                f"Recesión fuera de rango ({MIN_RECESSION_MM}–{MAX_RECESSION_MM} mm)"
            )
        return value


class MeasurementOut(MeasurementIn):
    id: uuid.UUID

    @computed_field
    @property
    def attachment_level(self) -> int | None:
        """Clinical attachment level, derived rather than stored: it is only
        meaningful when both of its terms were actually measured."""
        if self.probing_depth is None or self.recession is None:
            return None
        return self.probing_depth + self.recession

    model_config = {"from_attributes": True}


class PeriodontalToothIn(BaseModel):
    fdi_number: str
    absent: bool = False
    implant: bool = False
    mobility: int | None = None
    furcation: int | None = None
    notes: str | None = None

    _fdi = field_validator("fdi_number")(_validate_fdi)

    @field_validator("mobility")
    @classmethod
    def validate_mobility(cls, value: int | None) -> int | None:
        if value is not None and not 0 <= value <= MAX_MOBILITY:
            raise ValueError(f"Movilidad fuera de la escala de Miller (0–{MAX_MOBILITY})")
        return value

    @field_validator("furcation")
    @classmethod
    def validate_furcation(cls, value: int | None) -> int | None:
        if value is not None and not 0 <= value <= MAX_FURCATION:
            raise ValueError(f"Furca fuera de la escala de Hamp (0–{MAX_FURCATION})")
        return value


class PeriodontalToothOut(PeriodontalToothIn):
    id: uuid.UUID

    model_config = {"from_attributes": True}


class PeriodontogramCreate(BaseModel):
    professional_id: uuid.UUID | None = None
    notes: str | None = None
    teeth: list[PeriodontalToothIn] = Field(default_factory=list)
    measurements: list[MeasurementIn] = Field(default_factory=list)


class PeriodontalIndices(BaseModel):
    """The three numbers a periodontist actually reports, computed from the
    exam rather than typed in — so they can never disagree with it."""

    sites_recorded: int
    bleeding_sites: int
    plaque_sites: int
    bleeding_index: float
    plaque_index: float
    mean_probing_depth: float | None
    max_probing_depth: int | None
    sites_over_3mm: int
    sites_over_5mm: int


class PeriodontogramOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    professional_id: uuid.UUID | None
    created_by_id: uuid.UUID | None
    created_at: datetime
    previous_periodontogram_id: uuid.UUID | None
    notes: str | None
    type: str
    teeth: list[PeriodontalToothOut]
    measurements: list[MeasurementOut]

    @computed_field
    @property
    def indices(self) -> PeriodontalIndices:
        """Derived on the way out, from this exam's own sites. Storing these
        would let a stored index outlive a corrected measurement."""
        recorded = [m for m in self.measurements if m.probing_depth is not None]
        total = len(self.measurements)
        depths = [m.probing_depth for m in recorded if m.probing_depth is not None]
        bleeding = sum(1 for m in self.measurements if m.bleeding)
        plaque = sum(1 for m in self.measurements if m.plaque)
        return PeriodontalIndices(
            sites_recorded=len(recorded),
            bleeding_sites=bleeding,
            plaque_sites=plaque,
            # Percentages are over every charted site, not only the probed
            # ones: a site left unprobed still counts as charted.
            bleeding_index=round(bleeding / total * 100, 1) if total else 0.0,
            plaque_index=round(plaque / total * 100, 1) if total else 0.0,
            mean_probing_depth=round(sum(depths) / len(depths), 2) if depths else None,
            max_probing_depth=max(depths) if depths else None,
            sites_over_3mm=sum(1 for d in depths if d > 3),
            sites_over_5mm=sum(1 for d in depths if d > 5),
        )

    model_config = {"from_attributes": True}


class PeriodontogramSummary(BaseModel):
    id: uuid.UUID
    created_at: datetime
    type: str

    model_config = {"from_attributes": True}
