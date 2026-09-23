"""Import every module's models here so Base.metadata is complete for Alembic
autogenerate and for create_all in tests. Add a line whenever a new module
gains a models.py."""

from app.modules.appointments import models as appointments_models  # noqa: F401
from app.modules.audit import models as audit_models  # noqa: F401
from app.modules.budgets import models as budgets_models  # noqa: F401
from app.modules.clinics import models as clinics_models  # noqa: F401
from app.modules.prescriptions import models as prescriptions_models  # noqa: F401
from app.modules.documents import models as documents_models  # noqa: F401
from app.modules.consents import models as consents_models  # noqa: F401
from app.modules.clinical_evolution import models as clinical_evolution_models  # noqa: F401
from app.modules.diagnoses import models as diagnoses_models  # noqa: F401
from app.modules.inventory import models as inventory_models  # noqa: F401
from app.modules.laboratory import models as laboratory_models  # noqa: F401
from app.modules.medical_history import models as medical_history_models  # noqa: F401
from app.modules.imaging import models as imaging_models  # noqa: F401
from app.modules.odontogram import models as odontogram_models  # noqa: F401
from app.modules.periodontogram import models as periodontogram_models  # noqa: F401
from app.modules.ai_assist import models as ai_assist_models  # noqa: F401
from app.modules.messaging import models as messaging_models  # noqa: F401
from app.modules.patients import models as patients_models  # noqa: F401
from app.modules.portal import models as portal_models  # noqa: F401
from app.modules.privacy import models as privacy_models  # noqa: F401
from app.modules.payments import models as payments_models  # noqa: F401
from app.modules.professionals import models as professionals_models  # noqa: F401
from app.modules.treatment_plans import models as treatment_plans_models  # noqa: F401
from app.modules.treatments import models as treatments_models  # noqa: F401
from app.modules.users import models as users_models  # noqa: F401
