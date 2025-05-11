"""
Service xử lý logic cho phòng khám
"""
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db import crud
from app.models.database import ClinicCreate, ClinicUpdate

async def get_all_clinics(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    db: Session = None
) -> List[Dict[str, Any]]:
    """Lấy danh sách các phòng khám"""
    if search:
        clinics = crud.clinic.search_clinics(db, search, skip=skip, limit=limit)
    else:
        clinics = crud.clinic.get_all(db, skip=skip, limit=limit)
    
    # Lấy thông tin người tạo cho mỗi phòng khám
    result = []
    for clinic in clinics:
        # Loại bỏ _sa_instance_state
        clinic_dict = {k: v for k, v in clinic.__dict__.items() if k != "_sa_instance_state"}
        if clinic.created_by:
            creator = crud.user.get(db, clinic.created_by)
            if creator:
                # Chuyển creator thành dict sạch
                creator_dict = {k: v for k, v in creator.__dict__.items() if k != "_sa_instance_state"}
                clinic_dict["creator"] = creator_dict
        result.append(clinic_dict)
    
    return result

async def get_clinic_by_id(clinic_id: str, db: Session) -> Dict[str, Any]:
    """Lấy thông tin chi tiết của một phòng khám"""
    clinic = crud.clinic.get(db, id=clinic_id)
    if not clinic:
        raise HTTPException(status_code=404, detail="Không tìm thấy phòng khám")
    
    # Loại bỏ _sa_instance_state
    result = {k: v for k, v in clinic.__dict__.items() if k != "_sa_instance_state"}
    
    # Thêm thông tin người tạo
    if clinic.created_by:
        creator = crud.user.get(db, clinic.created_by)
        if creator:
            # Chuyển creator thành dict sạch
            creator_dict = {k: v for k, v in creator.__dict__.items() if k != "_sa_instance_state"}
            result["creator"] = creator_dict
    
    # Lấy các hình ảnh liên quan
    try:
        from app.services import image_management_service
        images = await image_management_service.get_images_for_object("clinic", clinic_id, db)
        result["images"] = images
    except Exception as e:
        result["images"] = []
    
    return result

async def create_clinic(clinic_data: ClinicCreate, creator_id: Optional[str], db: Session) -> Dict[str, Any]:
    """Tạo một phòng khám mới"""
    # Kiểm tra xem người tạo có tồn tại không
    if creator_id:
        creator = crud.user.get(db, id=creator_id)
        if not creator:
            raise HTTPException(status_code=404, detail="Người dùng không tồn tại")
        clinic_dict = clinic_data.model_dump()
        clinic_dict["created_by"] = creator_id
        clinic_data = ClinicCreate(**clinic_dict)
    
    clinic = crud.clinic.create(db, obj_in=clinic_data)
    
    # Trả về một dict sạch không chứa _sa_instance_state
    result = {k: v for k, v in clinic.__dict__.items() if k != "_sa_instance_state"}
    return result

async def update_clinic(clinic_id: str, clinic_data: ClinicUpdate, updater_id: Optional[str], db: Session) -> Dict[str, Any]:
    """Cập nhật thông tin phòng khám"""
    clinic = crud.clinic.get(db, id=clinic_id)
    if not clinic:
        raise HTTPException(status_code=404, detail="Không tìm thấy phòng khám")
    
    # Thêm thông tin người cập nhật
    if updater_id:
        updater = crud.user.get(db, id=updater_id)
        if not updater:
            raise HTTPException(status_code=404, detail="Người dùng không tồn tại")
        clinic_dict = clinic_data.model_dump(exclude_unset=True)
        clinic_dict["updated_by"] = updater_id
        clinic_data = ClinicUpdate(**clinic_dict)
    
    updated_clinic = crud.clinic.update(db, db_obj=clinic, obj_in=clinic_data)
    
    # Trả về một dict sạch không chứa _sa_instance_state
    result = {k: v for k, v in updated_clinic.__dict__.items() if k != "_sa_instance_state"}
    return result

async def delete_clinic(clinic_id: str, soft_delete: bool = True, deleted_by: Optional[str] = None, db: Session = None) -> Dict[str, Any]:
    """Xóa một phòng khám"""
    clinic = crud.clinic.get(db, id=clinic_id)
    if not clinic:
        raise HTTPException(status_code=404, detail="Không tìm thấy phòng khám")
    
    # Kiểm tra người xóa
    if deleted_by:
        deleter = crud.user.get(db, id=deleted_by)
        if not deleter:
            raise HTTPException(status_code=404, detail="Người dùng không tồn tại")
    
    if soft_delete:
        deleted_clinic = crud.clinic.soft_delete(db, id=clinic_id, deleted_by=deleted_by)
    else:
        deleted_clinic = crud.clinic.remove(db, id=clinic_id)
    
    return {"success": True, "clinic_id": clinic_id}

async def search_clinics(search_term: str, skip: int = 0, limit: int = 100, db: Session = None) -> List[Dict[str, Any]]:
    """Tìm kiếm phòng khám theo tên, mô tả hoặc địa chỉ"""
    clinics = crud.clinic.search_clinics(db, search_term, skip=skip, limit=limit)
    # Trả về danh sách các dict sạch không chứa _sa_instance_state
    return [{k: v for k, v in clinic.__dict__.items() if k != "_sa_instance_state"} for clinic in clinics] 