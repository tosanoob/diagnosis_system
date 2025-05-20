"""
Service xử lý và phân tích hình ảnh y khoa
"""
from typing import List
import io
import base64
import traceback
import numpy as np
from PIL import Image
import requests
from app.core.config import settings
from app.core.logging import logger

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

def encode_base64_images(images_batch: List[str]):
    """
    Nhận vào một batch các ảnh dạng base64 và trả về batch embeddings
    
    Args:
        images_batch: Danh sách các ảnh dạng base64
        
    Returns:
        numpy.ndarray: embeddings của tất cả ảnh, kích thước (batch_size, 1024)
    """
    try:
        # Gọi API embedding
        response = requests.post(
            f"{settings.IMAGE_EMBEDDING_URL}/encode",
            json={
                "images": images_batch,
                "texts": None
            }
        )
        response.raise_for_status()
        embeddings = response.json()["image_embeddings"]
        return np.array(embeddings)
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
    return encode_base64_images(base_64_batch)