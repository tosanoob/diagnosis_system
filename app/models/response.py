from pydantic import BaseModel, Field
from typing import List, Dict, Any, Tuple, TypeVar, Generic, Optional

T = TypeVar('T')

class Diagnose(BaseModel):
    """
    Model for a single diagnosis result
    """
    label: str = Field(..., description="The label of the diagnosis")
    confidence: float = Field(..., description="The confidence score of the diagnosis")
    description: str = Field(..., description="The description of the diagnosis")

class DiagnosisResponse(BaseModel):
    """
    Response model for diagnosis endpoint
    """
    labels: List[Tuple[str, Optional[float]]] = Field(..., description="The list of labels and their scores")
    response: str = Field(..., description="The response of the diagnosis")

class ImageOnlyMultiTurnResponse(BaseModel):
    """
    Response model for image-only multi-turn diagnosis endpoint
    """
    labels: Optional[List[Tuple[str, Optional[float]]]] = Field(..., description="The list of labels and their scores")
    response: str = Field(..., description="The response of the diagnosis")
    chat_history: List[Dict] = Field(..., description="The chat history of the conversation, include the new turn")

class ContextResponse(BaseModel):
    """
    Response model for context endpoint
    """
    labels: List[Tuple[str, Optional[float]]] = Field(..., description="The list of diagnosis labels")
    documents: List[str | List[str]] = Field(..., description="The list of documents")

class HealthResponse(BaseModel):
    """
    Response model for health check endpoint
    """
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    components: Dict[str, Dict[str, Any]] = Field(..., description="Status of various components") 

class PaginatedResponse(Generic[T]):
    """
    Response model cho các API hỗ trợ phân trang
    """
    items: List[T] = Field(..., description="Danh sách các items")
    pagination: Dict[str, Any] = Field(..., description="Thông tin phân trang")

    @classmethod
    def create(cls, items: List[T], total: int, skip: int, limit: int):
        """
        Tạo một đối tượng PaginatedResponse
        
        Args:
            items: Danh sách các items
            total: Tổng số records
            skip: Số records bỏ qua
            limit: Số records tối đa trên một trang
            
        Returns:
            PaginatedResponse: Đối tượng PaginatedResponse
        """
        total_pages = (total + limit - 1) // limit if limit > 0 else 1
        current_page = skip // limit + 1 if limit > 0 else 1
        
        return {
            "items": items,
            "pagination": {
                "total": total,
                "page": current_page,
                "size": limit,
                "pages": total_pages,
                "has_next": current_page < total_pages,
                "has_prev": current_page > 1
            }
        } 