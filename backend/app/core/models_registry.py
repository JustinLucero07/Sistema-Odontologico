"""Import every module's models here so Base.metadata is complete for Alembic
autogenerate and for create_all in tests. Add a line whenever a new module
gains a models.py."""

from app.modules.audit import models as audit_models  # noqa: F401
from app.modules.clinics import models as clinics_models  # noqa: F401
from app.modules.medical_history import models as medical_history_models  # noqa: F401
from app.modules.odontogram import models as odontogram_models  # noqa: F401
from app.modules.patients import models as patients_models  # noqa: F401
from app.modules.professionals import models as professionals_models  # noqa: F401
from app.modules.users import models as users_models  # noqa: F401
