from pydantic import BaseModel, Field
from typing import List, Optional, Union

class DiagnosisRequest(BaseModel):
    """
    Request model for diagnosis endpoints
    """
    image_base64: Optional[Union[str, List[str]]] = Field(
        default=None, 
        description="The image(s) of the patient encoded in base64 format"
    )
    text: Optional[str] = Field(
        default=None, 
        description="The text description of the patient regarding symptoms, affected areas, etc."
    )
    
    class Config:
        schema_extra = {
            "example": {
                "image_base64": "base64_encoded_string_here",
                "text": "Triệu chứng: Da bị ngứa, đỏ và có nhiều mảng tròn"
            }
        } 