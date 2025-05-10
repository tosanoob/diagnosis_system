from fastapi import APIRouter
from app.api.routes.diagnosis import router as diagnosis_router
from app.api.routes.health import router as health_router

router = APIRouter()

router.include_router(health_router, tags=["Health"])
router.include_router(diagnosis_router, prefix="/diagnosis", tags=["Diagnosis"])
