from fastapi import APIRouter, HTTPException
from app.models.request import DiagnosisRequest, ImageOnlyMultiTurnRequest
from app.models.response import DiagnosisResponse, ContextResponse, ImageOnlyMultiTurnResponse
from app.services.diagnosis_service import (
    get_diagnosis, get_context, image_diagnosis_only_async,
    get_first_diagnosis_v2, get_later_diagnosis_v2,
    get_first_stage_diagnosis_v3, get_second_stage_diagnosis_v3
)
from app.core.logging import logger
import traceback

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

@router.post("/image-only", response_model=DiagnosisResponse)
async def get_image_only_diagnosis(request: DiagnosisRequest):
    """
    Nhận vào image_base64, trả về chẩn đoán chi tiết
    """
    try:
        if not request.image_base64:    
            raise HTTPException(status_code=400, detail="Cần cung cấp image_base64")
            
        logger.app_info(f"Nhận request chẩn đoán: image={bool(request.image_base64)}")
        all_labels, label_documents = await image_diagnosis_only_async(request.image_base64)
        return ContextResponse(labels=all_labels, documents=label_documents)
    except Exception as e:
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Lỗi khi chẩn đoán: {str(e)}")

# @router.post("/image-only-multi-turn", response_model=ImageOnlyMultiTurnResponse)
# async def get_image_only_multi_turn_diagnosis(request: ImageOnlyMultiTurnRequest):
#     """
#     Nhận vào image_base64, trả về chẩn đoán chi tiết hoặc câu hỏi bổ sung thông tin
#     """
#     try:
#         if not request.image_base64 and not request.chat_history:
#             raise HTTPException(status_code=400, detail="Cần cung cấp image_base64 hoặc chat_history chứa image")
            
#         logger.app_info(f"Nhận request chẩn đoán: image={bool(request.image_base64)}")

#         if request.chat_history:
#             response, chat_history = await get_later_diagnosis_v2(request.chat_history, request.text)
#         else:
#             all_labels, response, chat_history = await get_first_diagnosis_v2(request.image_base64, request.text)
#         return ImageOnlyMultiTurnResponse(labels=all_labels, response=response, chat_history=chat_history)
#     except Exception as e:
#         logger.error(traceback.format_exc())
#         raise HTTPException(status_code=500, detail=f"Lỗi khi chẩn đoán: {str(e)}")

@router.post("/image-only-multi-turn", response_model=ImageOnlyMultiTurnResponse)
async def get_image_only_multi_turn_diagnosis(request: ImageOnlyMultiTurnRequest):
    """
    Nhận vào image_base64, trả về chẩn đoán chi tiết hoặc câu hỏi bổ sung thông tin
    """
    try:
        if not request.image_base64 and not request.chat_history:
            raise HTTPException(status_code=400, detail="Cần cung cấp image_base64 hoặc chat_history chứa image")
            
        logger.app_info(f"Nhận request chẩn đoán: image={bool(request.image_base64)}")
        all_labels = []
        if request.chat_history:
            response, chat_history = await get_second_stage_diagnosis_v3(request.chat_history, request.text)
        else:
            all_labels, response, chat_history = await get_first_stage_diagnosis_v3(request.image_base64, request.text)
        return ImageOnlyMultiTurnResponse(labels=all_labels, response=response, chat_history=chat_history)
    except Exception as e:
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Lỗi khi chẩn đoán: {str(e)}")
