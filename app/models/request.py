from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict

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

class ImageOnlyMultiTurnRequest(BaseModel):
    """
    Request model for image-only multi-turn diagnosis endpoints
    """
    image_base64: str = Field(..., description="The image of the patient encoded in base64 format")
    text: Optional[str] = Field(default=None, description="The text description of the patient regarding symptoms, affected areas, etc.")

    chat_history: Optional[List[Dict]] = Field(default=None, description="The chat history of the conversation, but without the latest message")