"""FastAPI server for image encoding using distilled model."""

import os
import json
import base64
import torch
import torchvision.transforms as transforms
from PIL import Image
from io import BytesIO
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import logging

# Import the distilled model
from runtime.trained_model.distilled_model import DistilledModel

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Request/Response models
class EncodeRequest(BaseModel):
    images: Optional[List[str]] = None
    texts: Optional[List[str]] = None

class EncodeResponse(BaseModel):
    image_embeddings: List[List[float]]

# Global variables
app = FastAPI(title="Image Encoding API", version="1.0.0")
model = None
device = None
transform = None

def load_model():
    """Load the distilled model from checkpoint."""
    global model, device, transform
    
    model_dir = "/home/cuong/workdir/src/chatbot-agentic/query_system/runtime/trained_model/embedding_distillation_20250518_125113"
    
    # Load model config
    config_path = os.path.join(model_dir, "model_config.json")
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    logger.info(f"Loading model with config: {config}")
    
    # Determine device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"Using device: {device}")
    
    # Initialize model
    model = DistilledModel(
        encoder_model_name=config["student_model_name"],
        pretrained=False,  # We'll load weights from checkpoint
        embedding_dim=config["embedding_dim"],
        num_classes=0  # No classification, only encoding
    )
    
    # Load model weights
    checkpoint_path = os.path.join(model_dir, "best_model.pt")
    checkpoint = torch.load(checkpoint_path, map_location=device)
    
    # Load state dict
    if 'model_state_dict' in checkpoint:
        model.load_state_dict(checkpoint['model_state_dict'])
    else:
        model.load_state_dict(checkpoint)
    
    model.to(device)
    model.eval()
    
    # Define image transforms
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    logger.info("Model loaded successfully")

def decode_base64_image(base64_string: str) -> Image.Image:
    """Decode base64 string to PIL Image."""
    try:
        # Remove data URL prefix if present
        if base64_string.startswith('data:image'):
            base64_string = base64_string.split(',')[1]
        
        # Decode base64
        image_data = base64.b64decode(base64_string)
        image = Image.open(BytesIO(image_data))
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
            
        return image
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 image: {str(e)}")

def preprocess_image(image: Image.Image) -> torch.Tensor:
    """Preprocess image for model input."""
    return transform(image)

@app.on_event("startup")
async def startup_event():
    """Load model on startup."""
    load_model()

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Image Encoding API is running"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "device": str(device) if device else None
    }

@app.post("/encode", response_model=EncodeResponse)
async def encode_images(request: EncodeRequest):
    """
    Encode images to embeddings.
    
    Args:
        request: Request containing images as base64 strings and texts
        
    Returns:
        Response containing image embeddings
    """
    try:
        if model is None:
            raise HTTPException(status_code=500, detail="Model not loaded")
        
        if not request.images:
            raise HTTPException(status_code=400, detail="No images provided")
        
        # Process images
        image_tensors = []
        for img_b64 in request.images:
            # Decode base64 image
            image = decode_base64_image(img_b64)
            
            # Preprocess image
            image_tensor = preprocess_image(image)
            image_tensors.append(image_tensor)
        
        # Stack images into batch
        batch_tensor = torch.stack(image_tensors).to(device)
        
        # Get embeddings
        with torch.no_grad():
            embeddings = model.encode(batch_tensor, normalize=True)
        
        # Convert to list format
        embeddings_list = embeddings.cpu().numpy().tolist()
        
        logger.info(f"Encoded {len(request.images)} images to embeddings")
        
        return EncodeResponse(image_embeddings=embeddings_list)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during encoding: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8126) 