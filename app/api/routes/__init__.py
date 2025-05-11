from fastapi import APIRouter
from app.api.routes.diagnosis import router as diagnosis_router
from app.api.routes.health import router as health_router
from app.api.routes.clinic import router as clinic_router
from app.api.routes.article import router as article_router
from app.api.routes.images import router as images_router
from app.api.routes.disease import router as disease_router
from app.api.routes.domain import router as domain_router
from app.api.routes.auth import router as auth_router

router = APIRouter()

router.include_router(health_router, tags=["Health"])
router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
router.include_router(diagnosis_router, prefix="/diagnosis", tags=["Diagnosis"])
router.include_router(clinic_router, prefix="/clinic", tags=["Clinic"])
router.include_router(article_router, prefix="/article", tags=["Article"])
router.include_router(images_router, prefix="/images", tags=["Images"])
router.include_router(disease_router, prefix="/diseases", tags=["Diseases"])
router.include_router(domain_router, prefix="/domains", tags=["Domains"])
