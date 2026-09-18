from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.modules.auth.router import router as auth_router
from app.modules.budgets.router import budgets_router, patient_budgets_router
from app.modules.clinics.router import router as clinics_router
from app.modules.diagnoses.router import router as diagnoses_router
from app.modules.medical_history.router import router as medical_history_router
from app.modules.odontogram.router import router as odontogram_router
from app.modules.patients.router import router as patients_router
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


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
