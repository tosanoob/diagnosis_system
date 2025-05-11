from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Path, Body
from sqlalchemy.orm import Session

from app.db.sqlite_service import get_db
from app.db import crud
from app.services import image_management_service
from app.models.database import Image, ImageUsage, ImageMap

router = APIRouter()

@router.post("/upload", response_model=dict)
async def upload_image(
    file: UploadFile = File(...),
    object_type: str = Form(...),
    object_id: str = Form(...),
    usage: str = Form(...),
    uploaded_by: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Tải lên hình ảnh mới và liên kết với đối tượng
    """
    result = await image_management_service.save_image(
        file=file,
        object_type=object_type,
        object_id=object_id,
        usage=usage,
        db=db,
        uploaded_by=uploaded_by
    )
    return result

@router.post("/bulk-upload", response_model=dict)
async def bulk_upload_images(
    files: List[UploadFile] = File(...),
    object_type: str = Form(...),
    object_id: str = Form(...),
    usages: List[str] = Form(...),
    uploaded_by: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Tải lên nhiều hình ảnh cùng lúc và liên kết với một đối tượng
    """
    result = await image_management_service.bulk_upload_images(
        files=files,
        object_type=object_type,
        object_id=object_id,
        usages=usages,
        db=db,
        uploaded_by=uploaded_by
    )
    return result

@router.get("/object/{object_type}/{object_id}", response_model=List[dict])
async def get_images_for_object(
    object_type: str = Path(...),
    object_id: str = Path(...),
    db: Session = Depends(get_db)
):
    """
    Lấy tất cả hình ảnh liên quan đến một đối tượng
    """
    return await image_management_service.get_images_for_object(
        object_type=object_type,
        object_id=object_id,
        db=db
    )

@router.get("/object/{object_type}/{object_id}/{usage}", response_model=Optional[dict])
async def get_image_by_usage(
    object_type: str = Path(...),
    object_id: str = Path(...),
    usage: str = Path(...),
    db: Session = Depends(get_db)
):
    """
    Lấy hình ảnh của một đối tượng theo loại sử dụng (thumbnail, cover)
    """
    return await image_management_service.get_image_by_usage(
        object_type=object_type,
        object_id=object_id,
        usage=usage,
        db=db
    )

@router.delete("/{image_id}", response_model=dict)
async def delete_image(
    image_id: str = Path(...),
    db: Session = Depends(get_db)
):
    """
    Xóa một hình ảnh và tất cả các liên kết của nó
    """
    success = await image_management_service.delete_image(
        image_id=image_id,
        db=db
    )
    return {"success": success}

@router.put("/usage/{object_type}/{object_id}", response_model=Optional[dict])
async def update_image_usage(
    object_type: str = Path(...),
    object_id: str = Path(...),
    old_usage: str = Query(...),
    new_usage: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Cập nhật loại sử dụng của hình ảnh
    """
    result = await image_management_service.update_image_usage(
        object_type=object_type,
        object_id=object_id,
        old_usage=old_usage,
        new_usage=new_usage,
        db=db
    )
    return result

@router.get("/usages", response_model=List[ImageUsage])
def get_image_usages(
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách các loại sử dụng hình ảnh
    """
    return crud.image_usage.get_all(db)

@router.get("/statistics", response_model=dict)
async def get_statistics(
    db: Session = Depends(get_db)
):
    """
    Lấy thống kê về hình ảnh trong hệ thống
    """
    return await image_management_service.get_image_statistics(db)

@router.post("/validate", response_model=dict)
async def validate_image(
    file: UploadFile = File(...)
):
    """
    Kiểm tra tính hợp lệ của hình ảnh trước khi tải lên
    """
    is_valid, error_message = await image_management_service.validate_image(file)
    return {
        "valid": is_valid,
        "error": error_message
    }

@router.delete("/object/{object_type}/{object_id}", response_model=dict)
async def delete_images_for_object(
    object_type: str = Path(...),
    object_id: str = Path(...),
    db: Session = Depends(get_db)
):
    """
    Xóa tất cả hình ảnh liên quan đến một đối tượng
    """
    images = await image_management_service.get_images_for_object(
        object_type=object_type,
        object_id=object_id,
        db=db
    )
    
    deleted_count = 0
    for image_data in images:
        image_id = image_data["image"]["id"]
        try:
            await image_management_service.delete_image(image_id=image_id, db=db)
            deleted_count += 1
        except Exception as e:
            pass
    
    return {
        "success": True,
        "deleted_count": deleted_count,
        "total_images": len(images)
    } 