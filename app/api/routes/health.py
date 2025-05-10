from fastapi import APIRouter, Depends
from app.models.response import HealthResponse
from app.core.config import settings
import os
import platform
import sys

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Endpoint kiểm tra trạng thái hoạt động của API
    """
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "components": {
            "system": {
                "python_version": sys.version,
                "platform": platform.platform(),
                "processor": platform.processor()
            },
            "paths": {
                "chroma_data_exists": os.path.exists(settings.CHROMA_DATA_PATH),
                "medimageinsights_model_exists": os.path.exists(settings.MEDIMAGEINSIGHTS_MODEL_DIR)
            }
        }
    } 