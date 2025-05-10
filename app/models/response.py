from pydantic import BaseModel, Field
from typing import List, Dict, Any, Tuple

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
    labels: List[Tuple[str, float]] = Field(..., description="The list of labels and their scores")
    response: str = Field(..., description="The response of the diagnosis")

class ContextResponse(BaseModel):
    """
    Response model for context endpoint
    """
    labels: List[Tuple[str, float]] = Field(..., description="The list of diagnosis labels")
    documents: List[str] = Field(..., description="The list of documents")

class HealthResponse(BaseModel):
    """
    Response model for health check endpoint
    """
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    components: Dict[str, Dict[str, Any]] = Field(..., description="Status of various components") 