"""
Service quản lý và xử lý hình ảnh
"""
import os
import shutil
import uuid
from typing import Optional, List, Dict, Any, BinaryIO, Union, Tuple
from datetime import datetime, timezone
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
import imghdr
import io
from PIL import Image as PILImage

from app.core.config import settings
from app.core.logging import logger
from app.db import crud
from app.models.database import ImageCreate, ImageMapCreate, ImageUsageCreate

# Đường dẫn gốc cho thư mục lưu trữ hình ảnh
IMAGE_ROOT_DIR = "runtime/image"

# Các loại object_type hợp lệ
VALID_OBJECT_TYPES = ["disease", "article", "clinic"]

# Các loại usage hợp lệ
VALID_USAGES = ["thumbnail", "cover"]

# Kích thước chunk khi đọc file (8MB)
CHUNK_SIZE = 8 * 1024 * 1024

# Giới hạn kích thước file (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# Các loại mime hợp lệ
VALID_MIME_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"]

# Kích thước tối đa và tối thiểu của ảnh
MIN_WIDTH = 100
MIN_HEIGHT = 100
MAX_WIDTH = 5000
MAX_HEIGHT = 5000

async def validate_image(file: UploadFile) -> Tuple[bool, Optional[str]]:
    """
    Kiểm tra tính hợp lệ của ảnh trước khi tải lên
    
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    # Kiểm tra mime type
    content_type = file.content_type
    if content_type not in VALID_MIME_TYPES:
        return False, f"Loại tệp không hợp lệ. Chỉ chấp nhận: {', '.join(VALID_MIME_TYPES)}"
    
    # Đọc một phần của file để kiểm tra
    file_header = await file.read(1024)
    
    # Kiểm tra định dạng thật sự của file
    file_format = imghdr.what(None, file_header)
    if not file_format:
        await file.seek(0)
        return False, "Tệp không phải là hình ảnh hợp lệ"
    
    # Kiểm tra kích thước file
    await file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    if file_size > MAX_FILE_SIZE:
        await file.seek(0)
        return False, f"Kích thước tệp vượt quá giới hạn cho phép ({MAX_FILE_SIZE / 1024 / 1024}MB)"
    
    # Kiểm tra kích thước ảnh
    try:
        await file.seek(0)
        img = PILImage.open(io.BytesIO(await file.read()))
        width, height = img.size
        
        if width < MIN_WIDTH or height < MIN_HEIGHT:
            await file.seek(0)
            return False, f"Ảnh quá nhỏ. Kích thước tối thiểu: {MIN_WIDTH}x{MIN_HEIGHT}"
        
        if width > MAX_WIDTH or height > MAX_HEIGHT:
            await file.seek(0)
            return False, f"Ảnh quá lớn. Kích thước tối đa: {MAX_WIDTH}x{MAX_HEIGHT}"
    except Exception as e:
        await file.seek(0)
        return False, f"Lỗi khi kiểm tra kích thước ảnh: {str(e)}"
    
    # Reset con trỏ đọc file về đầu
    await file.seek(0)
    return True, None

async def init_image_usages(db: Session):
    """
    Khởi tạo các loại usage cho hình ảnh
    """
    try:
        # Kiểm tra xem usage "thumbnail" đã tồn tại chưa
        thumbnail = crud.image_usage.get(db, "thumbnail")
        if not thumbnail:
            thumbnail_data = ImageUsageCreate(
                usage="thumbnail",
                description="Hình ảnh nhỏ dùng cho hiển thị danh sách"
            )
            crud.image_usage.create(db, obj_in=thumbnail_data)
            logger.app_info("Created thumbnail image usage")
        
        # Kiểm tra xem usage "cover" đã tồn tại chưa
        cover = crud.image_usage.get(db, "cover")
        if not cover:
            cover_data = ImageUsageCreate(
                usage="cover",
                description="Hình ảnh bìa hiển thị đầy đủ"
            )
            crud.image_usage.create(db, obj_in=cover_data)
            logger.app_info("Created cover image usage")
            
    except Exception as e:
        logger.error(f"Error initializing image usages: {str(e)}")
        raise

async def save_image(
    file: UploadFile,
    object_type: str,
    object_id: str,
    usage: str,
    db: Session,
    uploaded_by: Optional[str] = None
) -> Dict[str, Any]:
    """
    Lưu hình ảnh và tạo các bản ghi cần thiết trong cơ sở dữ liệu
    """
    if object_type not in VALID_OBJECT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid object_type. Must be one of: {', '.join(VALID_OBJECT_TYPES)}")
    
    if usage not in VALID_USAGES:
        raise HTTPException(status_code=400, detail=f"Invalid usage. Must be one of: {', '.join(VALID_USAGES)}")
    
    # Kiểm tra tính hợp lệ của ảnh
    is_valid, error_message = await validate_image(file)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_message)
    
    # Tạo tên file duy nhất
    file_extension = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
    file_name = f"{uuid.uuid4()}{file_extension}"
    
    # Đường dẫn lưu trữ
    rel_path = f"{object_type}/{file_name}"
    file_path = os.path.join(IMAGE_ROOT_DIR, rel_path)
    
    try:
        # Đảm bảo thư mục tồn tại
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Lưu file theo chunks để giảm sử dụng bộ nhớ
        with open(file_path, "wb") as buffer:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                buffer.write(chunk)
        
        # Tạo bản ghi Image
        image_data = ImageCreate(
            base_url=settings.IMAGE_BASE_URL if hasattr(settings, "IMAGE_BASE_URL") else "/static/images",
            rel_path=rel_path,
            mime_type=file.content_type or "image/jpeg",
            uploaded_by=uploaded_by
        )
        
        image = crud.image.create(db, obj_in=image_data)
        
        # Kiểm tra xem đã có bản ghi ImageMap nào cho đối tượng và usage này chưa
        existing_map = crud.image_map.get_by_object_and_usage(db, object_type, object_id, usage)
        
        # Nếu có, xóa bản ghi cũ
        if existing_map:
            crud.image_map.remove(db, id=existing_map.id)
        
        # Tạo bản ghi ImageMap
        image_map_data = ImageMapCreate(
            image_id=image.id,
            object_type=object_type,
            object_id=object_id,
            usage=usage
        )
        
        image_map = crud.image_map.create(db, obj_in=image_map_data)
        
        return {
            "image": image,
            "image_map": image_map
        }
        
    except Exception as e:
        logger.error(f"Error saving image: {str(e)}")
        # Xóa file nếu có lỗi
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Error saving image: {str(e)}")

async def bulk_upload_images(
    files: List[UploadFile],
    object_type: str,
    object_id: str,
    usages: List[str],
    db: Session,
    uploaded_by: Optional[str] = None
) -> Dict[str, Any]:
    """
    Tải lên nhiều hình ảnh cùng lúc và liên kết với một đối tượng
    
    Args:
        files: Danh sách các file hình ảnh
        object_type: Loại đối tượng (disease, article, clinic)
        object_id: ID của đối tượng
        usages: Danh sách các loại sử dụng tương ứng với từng file
        db: Database session
        uploaded_by: ID của người tải lên
        
    Returns:
        Dict với kết quả tải lên
    """
    if object_type not in VALID_OBJECT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid object_type. Must be one of: {', '.join(VALID_OBJECT_TYPES)}")
    
    if len(files) != len(usages):
        raise HTTPException(status_code=400, detail="Number of files and usages must match")
    
    # Kiểm tra các loại usage
    for usage in usages:
        if usage not in VALID_USAGES:
            raise HTTPException(status_code=400, detail=f"Invalid usage: {usage}. Must be one of: {', '.join(VALID_USAGES)}")
    
    results = []
    errors = []
    
    for i, (file, usage) in enumerate(zip(files, usages)):
        try:
            # Tải lên từng ảnh
            result = await save_image(
                file=file,
                object_type=object_type,
                object_id=object_id,
                usage=usage,
                db=db,
                uploaded_by=uploaded_by
            )
            results.append(result)
        except HTTPException as e:
            errors.append({
                "file_index": i,
                "filename": file.filename,
                "usage": usage,
                "error": e.detail
            })
        except Exception as e:
            errors.append({
                "file_index": i,
                "filename": file.filename,
                "usage": usage,
                "error": str(e)
            })
    
    return {
        "success": len(results),
        "failed": len(errors),
        "total": len(files),
        "results": results,
        "errors": errors
    }

async def get_images_for_object(
    object_type: str,
    object_id: str,
    db: Session
) -> List[Dict[str, Any]]:
    """
    Lấy tất cả hình ảnh cho một đối tượng
    """
    if object_type not in VALID_OBJECT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid object_type. Must be one of: {', '.join(VALID_OBJECT_TYPES)}")
    
    try:
        return crud.image_map.get_with_images(db, object_type, object_id)
    except Exception as e:
        logger.error(f"Error getting images for object: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting images: {str(e)}")

async def get_image_by_usage(
    object_type: str,
    object_id: str,
    usage: str,
    db: Session
) -> Optional[Dict[str, Any]]:
    """
    Lấy hình ảnh theo loại sử dụng cho một đối tượng
    """
    if object_type not in VALID_OBJECT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid object_type. Must be one of: {', '.join(VALID_OBJECT_TYPES)}")
    
    if usage not in VALID_USAGES:
        raise HTTPException(status_code=400, detail=f"Invalid usage. Must be one of: {', '.join(VALID_USAGES)}")
    
    try:
        image_map = crud.image_map.get_by_object_and_usage(db, object_type, object_id, usage)
        if not image_map:
            return None
        
        image = crud.image.get(db, image_map.image_id)
        if not image:
            return None
        
        return {
            "image_map": image_map,
            "image": image
        }
    except Exception as e:
        logger.error(f"Error getting image by usage: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting image: {str(e)}")

async def delete_image(image_id: str, db: Session) -> bool:
    """
    Xóa một hình ảnh và tất cả các bản ghi liên quan
    """
    try:
        # Lấy thông tin hình ảnh
        image = crud.image.get(db, image_id)
        if not image:
            raise HTTPException(status_code=404, detail="Image not found")
        
        # Lấy các bản ghi image_map
        image_maps = crud.image_map.get_by_image(db, image_id)
        
        # Xóa các bản ghi image_map
        for image_map in image_maps:
            crud.image_map.remove(db, id=image_map.id)
        
        # Xóa file vật lý
        file_path = os.path.join(IMAGE_ROOT_DIR, image.rel_path)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Xóa bản ghi image
        crud.image.remove(db, id=image_id)
        
        return True
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting image: {str(e)}")

async def update_image_usage(
    object_type: str,
    object_id: str,
    old_usage: str,
    new_usage: str,
    db: Session
) -> Optional[Dict[str, Any]]:
    """
    Cập nhật loại sử dụng của một hình ảnh
    """
    if object_type not in VALID_OBJECT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid object_type. Must be one of: {', '.join(VALID_OBJECT_TYPES)}")
    
    if old_usage not in VALID_USAGES or new_usage not in VALID_USAGES:
        raise HTTPException(status_code=400, detail=f"Invalid usage. Must be one of: {', '.join(VALID_USAGES)}")
    
    try:
        # Tìm bản ghi cần cập nhật
        image_map = crud.image_map.get_by_object_and_usage(db, object_type, object_id, old_usage)
        if not image_map:
            return None
        
        # Kiểm tra xem đã có bản ghi nào với usage mới chưa
        existing_map = crud.image_map.get_by_object_and_usage(db, object_type, object_id, new_usage)
        
        # Nếu có, xóa bản ghi cũ
        if existing_map:
            crud.image_map.remove(db, id=existing_map.id)
        
        # Cập nhật usage
        image_map.usage = new_usage
        db.add(image_map)
        db.commit()
        db.refresh(image_map)
        
        # Lấy thông tin hình ảnh
        image = crud.image.get(db, image_map.image_id)
        
        return {
            "image_map": image_map,
            "image": image
        }
    except Exception as e:
        logger.error(f"Error updating image usage: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating image usage: {str(e)}")

async def get_image_statistics(db: Session) -> Dict[str, Any]:
    """
    Lấy thống kê về hình ảnh trong hệ thống
    """
    try:
        # Tổng số ảnh
        total_images = crud.image.count(db)
        
        # Số lượng ảnh theo object_type
        stats_by_type = {}
        for object_type in VALID_OBJECT_TYPES:
            query = f"SELECT COUNT(*) FROM image_map WHERE object_type = '{object_type}'"
            result = db.execute(query).scalar()
            stats_by_type[object_type] = result
        
        # Số lượng ảnh theo usage
        stats_by_usage = {}
        for usage in VALID_USAGES:
            query = f"SELECT COUNT(*) FROM image_map WHERE usage = '{usage}'"
            result = db.execute(query).scalar()
            stats_by_usage[usage] = result
        
        # Kiểm tra tồn tại của các file vật lý
        missing_files = 0
        for image in crud.image.get_all(db):
            file_path = os.path.join(IMAGE_ROOT_DIR, image.rel_path)
            if not os.path.exists(file_path):
                missing_files += 1
        
        return {
            "total_images": total_images,
            "by_object_type": stats_by_type,
            "by_usage": stats_by_usage,
            "missing_files": missing_files
        }
    except Exception as e:
        logger.error(f"Error getting image statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting image statistics: {str(e)}") 