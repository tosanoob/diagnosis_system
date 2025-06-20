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
import argparse

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
model_dir = None

def load_model(model_directory: str):
    """Load the distilled model from checkpoint."""
    global model, device, transform
    
    if not os.path.exists(model_directory):
        raise FileNotFoundError(f"Model directory không tồn tại: {model_directory}")
    
    # Load model config
    config_path = os.path.join(model_directory, "model_config.json")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Model config không tồn tại: {config_path}")
        
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    logger.info(f"Loading model from: {model_directory}")
    logger.info(f"Model config: {config}")
    
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
    checkpoint_path = os.path.join(model_directory, "best_model.pt")
    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(f"Model checkpoint không tồn tại: {checkpoint_path}")
        
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
    load_model(model_dir)

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

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="FastAPI server for image encoding using distilled model")
    
    parser.add_argument(
        "--model_dir",
        type=str,
        default="runtime/trained_model/efficientnet_v2_m",
        help="Đường dẫn tới thư mục chứa model đã train (default: %(default)s)"
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host để bind server (default: %(default)s)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8126,
        help="Port để bind server (default: %(default)s)"
    )
    
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    model_dir = args.model_dir
    
    logger.info(f"Khởi chạy server với model_dir: {model_dir}")
    uvicorn.run(app, host=args.host, port=args.port) 