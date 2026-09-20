from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.modules.appointments.router import patient_router as patient_appointments_router
from app.modules.appointments.router import router as appointments_router
from app.modules.auth.router import router as auth_router
from app.modules.budgets.router import budgets_router, patient_budgets_router
from app.modules.clinical_evolution.router import patient_router as patient_evolutions_router
from app.modules.clinical_evolution.router import router as evolutions_router
from app.modules.clinics.router import router as clinics_router
from app.modules.consents.router import patient_router as patient_consents_router
from app.modules.consents.router import router as consents_router
from app.modules.documents.router import patient_router as patient_documents_router
from app.modules.documents.router import router as documents_router
from app.modules.prescriptions.router import router as prescriptions_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.diagnoses.router import router as diagnoses_router
from app.modules.imaging.router import patient_router as patient_images_router
from app.modules.imaging.router import router as images_router
from app.modules.medical_history.router import router as medical_history_router
from app.modules.odontogram.router import router as odontogram_router
from app.modules.patients.router import router as patients_router
from app.modules.payments.router import patient_router as patient_finance_router
from app.modules.payments.router import router as finance_router
from app.modules.periodontogram.router import catalog_router as periodontogram_catalog_router
from app.modules.periodontogram.router import router as periodontogram_router
from app.modules.professionals.router import router as professionals_router
from app.modules.treatment_plans.router import patient_plans_router, plans_router
from app.modules.treatments.router import router as treatments_router
from app.modules.users.router import router as users_router

settings = get_settings()

app = FastAPI(title=settings.APP_NAME, version="0.1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Browsers cache a preflight — including a failed one. The default 600s
    # means a restart during development can lock the UI out for ten minutes.
    max_age=60,
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(clinics_router)
app.include_router(professionals_router)
app.include_router(patients_router)
app.include_router(medical_history_router)
app.include_router(odontogram_router)
app.include_router(diagnoses_router)
app.include_router(treatments_router)
app.include_router(patient_plans_router)
app.include_router(plans_router)
app.include_router(patient_budgets_router)
app.include_router(budgets_router)
app.include_router(appointments_router)
app.include_router(patient_appointments_router)
app.include_router(dashboard_router)
app.include_router(patient_evolutions_router)
app.include_router(evolutions_router)
app.include_router(prescriptions_router)
app.include_router(patient_consents_router)
app.include_router(consents_router)
app.include_router(patient_documents_router)
app.include_router(documents_router)
app.include_router(periodontogram_catalog_router)
app.include_router(periodontogram_router)
app.include_router(patient_images_router)
app.include_router(images_router)
app.include_router(patient_finance_router)
app.include_router(finance_router)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
