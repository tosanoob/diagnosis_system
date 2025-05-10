from fastapi import APIRouter, HTTPException
from app.models.request import DiagnosisRequest
from app.models.response import DiagnosisResponse, ContextResponse
from app.services.diagnosis_service import get_diagnosis, get_context
from app.core.logging import logger

router = APIRouter()

@router.post("/analyze", response_model=DiagnosisResponse)
async def analyze_diagnosis(request: DiagnosisRequest):
    """
    Nhận vào text hoặc/và image_base64, trả về chẩn đoán chi tiết
    """
    try:
        if not request.text and not request.image_base64:
            raise HTTPException(status_code=400, detail="Cần cung cấp ít nhất một trong hai: text hoặc image_base64")
            
        logger.app_info(f"Nhận request chẩn đoán: text={bool(request.text)}, image={bool(request.image_base64)}")
        all_labels, response = await get_diagnosis(
            text=request.text,
            image_base64=request.image_base64
        )
        return DiagnosisResponse(labels=all_labels, response=response)
    except Exception as e:
        logger.error(f"Lỗi khi chẩn đoán: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi chẩn đoán: {str(e)}")

@router.post("/context", response_model=ContextResponse)
async def get_diagnosis_context(request: DiagnosisRequest):
    """
    Nhận vào text hoặc/và image_base64, trả về các thông tin từ cơ sở dữ liệu liên quan đến bệnh
    """
    try:
        if not request.text and not request.image_base64:
            raise HTTPException(status_code=400, detail="Cần cung cấp ít nhất một trong hai: text hoặc image_base64")
            
        logger.app_info(f"Nhận request lấy context: text={bool(request.text)}, image={bool(request.image_base64)}")
        all_labels, label_documents = await get_context(
            text=request.text,
            image_base64=request.image_base64
        )
        return ContextResponse(labels=all_labels, documents=label_documents)
    except Exception as e:
        logger.error(f"Lỗi khi lấy context: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy context: {str(e)}") 