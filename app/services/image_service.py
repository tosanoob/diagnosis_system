"""
Service xử lý và phân tích hình ảnh y khoa
"""
from typing import List
import io
import base64
import sys
import os
import traceback
import numpy as np
from PIL import Image
from app.core.config import settings
from app.core.logging import logger

# Thêm đường dẫn tuyệt đối đến MedImageInsights
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MEDIMAGEINSIGHTS_PATH = os.path.join(WORKSPACE_ROOT, "runtime/models/MedImageInsights")

# Đảm bảo thư mục tồn tại
if not os.path.exists(MEDIMAGEINSIGHTS_PATH):
    logger.error(f"MedImageInsights directory not found at: {MEDIMAGEINSIGHTS_PATH}")
    raise FileNotFoundError(f"MedImageInsights directory not found at: {MEDIMAGEINSIGHTS_PATH}")

# Thêm đường dẫn vào sys.path
sys.path.insert(0, MEDIMAGEINSIGHTS_PATH)
sys.path.insert(0, os.path.join(MEDIMAGEINSIGHTS_PATH, "MedImageInsight"))

# Log đường dẫn để debug
logger.app_info(f"MedImageInsights path: {MEDIMAGEINSIGHTS_PATH}")
logger.app_info(f"Current sys.path: {sys.path}")

try:
    # Import trực tiếp từ file, không phải từ package
    sys.path.insert(0, MEDIMAGEINSIGHTS_PATH)
    from medimageinsightmodel import MedImageInsight
    logger.app_info("Successfully imported MedImageInsightModel")
except ImportError as e:
    logger.error(f"Failed to import MedImageInsightModel: {str(e)}")
    # Liệt kê các file Python trong thư mục
    python_files = [f for f in os.listdir(MEDIMAGEINSIGHTS_PATH) if f.endswith('.py')]
    logger.error(f"Python files in directory: {python_files}")
    raise

# Model directory is relative to workspace root
model_dir = os.path.join(WORKSPACE_ROOT, "runtime/models/MedImageInsights/2024.09.27")
logger.app_info(f"Loading model from: {model_dir}")

if not os.path.exists(model_dir):
    logger.error(f"Model directory not found at: {model_dir}")
    raise FileNotFoundError(f"Model directory not found at: {model_dir}")

# Initialize model
try:
    classifier = MedImageInsight(
        model_dir=model_dir,
        vision_model_name=settings.MEDIMAGEINSIGHTS_VISION_MODEL,
        language_model_name=settings.MEDIMAGEINSIGHTS_LANGUAGE_MODEL
    )
    classifier.load_model()
    logger.app_info("Model loaded successfully")
except Exception as e:
    logger.error(f"Failed to load model: {str(e)}")
    logger.error(traceback.format_exc())
    raise

def numpy_to_base64(img_array):
    """
    Chuyển đổi numpy array thành chuỗi base64
    
    Args:
        img_array (numpy.ndarray): Ảnh dạng numpy array (định dạng từ albumentation)
    
    Returns:
        str: Chuỗi base64 của ảnh
    """
    # Chuyển đổi sang kiểu uint8 nếu chưa phải
    if img_array.dtype != np.uint8:
        img_array = (img_array * 255).astype(np.uint8)
    # Xử lý ảnh RGBA (4 kênh) bằng cách chuyển đổi sang RGB
    if len(img_array.shape) == 3 and img_array.shape[2] == 4:
        # Tạo nền trắng
        white_background = np.ones((img_array.shape[0], img_array.shape[1], 3), dtype=np.uint8) * 255
        # Lấy kênh alpha
        alpha = img_array[:, :, 3:4] / 255.0
        # Trộn ảnh RGB với nền trắng dựa trên kênh alpha
        rgb = img_array[:, :, :3]
        img_array = (rgb * alpha + white_background * (1 - alpha)).astype(np.uint8)
    # Nếu ảnh là grayscale (2D), chuyển sang RGB
    if len(img_array.shape) == 2:
        img_array = np.stack([img_array] * 3, axis=2)
    
    # Chuyển đổi từ [H, W, C] sang định dạng RGB PIL Image
    img_pil = Image.fromarray(img_array)
    
    # Chuyển đổi PIL Image sang base64
    buffer = io.BytesIO()
    img_pil.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

def predict(images: List[str], labels: List[str], multilabel: bool = False):
    """
    Dự đoán nhãn cho các hình ảnh
    
    Args:
        images: Danh sách các ảnh dạng base64
        labels: Danh sách các nhãn
        multilabel: Có cho phép dự đoán nhiều nhãn hay không
        
    Returns:
        Kết quả dự đoán
    """
    try:
        results = classifier.predict(
            images=images,
            labels=labels,
            multilabel=multilabel
        )
        return results
    except Exception as e:
        logger.error(f"Lỗi khi dự đoán: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def encode_base64_images(images_batch: List[str]):
    """
    Nhận vào một batch các ảnh dạng base64 và trả về batch embeddings
    
    Args:
        images_batch: Danh sách các ảnh dạng base64
        
    Returns:
        numpy.ndarray: embeddings của tất cả ảnh, kích thước (batch_size, 1024)
    """
    try:
        embeddings = classifier.encode(images=images_batch)["image_embeddings"]
        return embeddings
    except Exception as e:
        logger.error(f"Lỗi khi mã hóa ảnh: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def encode_numpy_images(images_batch: List[np.ndarray]):
    """
    Nhận vào một batch các ảnh dạng numpy array và trả về batch embeddings
    
    Args:
        images_batch: Danh sách các ảnh dạng numpy array
        
    Returns:
        numpy.ndarray: embeddings của tất cả ảnh, kích thước (batch_size, 1024)
    """
    base_64_batch = [numpy_to_base64(img) for img in images_batch]
    embeddings = classifier.encode(images=base_64_batch)["image_embeddings"]
    
    # Ghép tất cả embedding thành tensor với kích thước (batch_size, 1024)
    return embeddings