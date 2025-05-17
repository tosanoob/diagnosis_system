"""
Service xử lý logic cho phòng khám
"""
from typing import List, Dict, Any, Optional, Tuple
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.db import crud
from app.models.database import ClinicCreate, ClinicUpdate
from app.services.utils import filter_user_data

async def get_all_clinics(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    include_deleted: bool = False,
    db: Session = None
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Lấy danh sách các phòng khám
    
    Returns:
        Tuple[List[Dict[str, Any]], int]: Danh sách phòng khám và tổng số records
    """
    if search:
        clinics = get_clinics_by_search(search, skip, limit, include_deleted, db)
        total = count_clinics_by_search(search, include_deleted, db)
    else:
        clinics = get_all_clinics_base(skip, limit, include_deleted, db)
        total = count_all_clinics(include_deleted, db)
    
    # Trả về danh sách với thông tin phù hợp
    result = []
    for clinic in clinics:
        # Loại bỏ _sa_instance_state
        clinic_dict = {k: v for k, v in clinic.__dict__.items() if k != "_sa_instance_state"}
        
        # Lấy các hình ảnh liên quan
        try:
            from app.services import image_management_service
            images = await image_management_service.get_images_for_object("clinic", clinic.id, db)
            clinic_dict["images"] = images
        except Exception as e:
            clinic_dict["images"] = []
        
        result.append(clinic_dict)
    
    return result, total

def get_clinics_by_search(search_term: str, skip: int, limit: int, include_deleted: bool, db: Session):
    """Helper function để tìm kiếm phòng khám"""
    search_pattern = f"%{search_term}%"
    query = db.query(crud.clinic.model).filter(
        or_(
            crud.clinic.model.name.ilike(search_pattern),
            crud.clinic.model.description.ilike(search_pattern),
            crud.clinic.model.location.ilike(search_pattern)
        )
    )
    
    if not include_deleted:
        query = query.filter(crud.clinic.model.deleted_at.is_(None))
        
    return query.offset(skip).limit(limit).all()

def get_all_clinics_base(skip: int, limit: int, include_deleted: bool, db: Session):
    """Helper function để lấy tất cả phòng khám"""
    query = db.query(crud.clinic.model)
    
    if not include_deleted:
        query = query.filter(crud.clinic.model.deleted_at.is_(None))
        
    return query.offset(skip).limit(limit).all()

def count_clinics_by_search(search_term: str, include_deleted: bool, db: Session) -> int:
    """Helper function để đếm số phòng khám theo kết quả tìm kiếm"""
    search_pattern = f"%{search_term}%"
    query = db.query(func.count(crud.clinic.model.id)).filter(
        or_(
            crud.clinic.model.name.ilike(search_pattern),
            crud.clinic.model.description.ilike(search_pattern),
            crud.clinic.model.location.ilike(search_pattern)
        )
    )
    
    if not include_deleted:
        query = query.filter(crud.clinic.model.deleted_at.is_(None))
        
    return query.scalar()

def count_all_clinics(include_deleted: bool, db: Session) -> int:
    """Helper function để đếm tất cả phòng khám"""
    query = db.query(func.count(crud.clinic.model.id))
    
    if not include_deleted:
        query = query.filter(crud.clinic.model.deleted_at.is_(None))
        
    return query.scalar()

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
            # Lọc thông tin nhạy cảm từ creator
            creator_dict = filter_user_data({k: v for k, v in creator.__dict__.items() if k != "_sa_instance_state"})
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
        
        # Chuyển đổi từ Pydantic model sang dict
        clinic_dict = clinic_data.model_dump()
        # Thêm thông tin người tạo
        clinic_dict["created_by"] = creator_id
        # Cập nhật updated_by cùng với created_by
        clinic_dict["updated_by"] = creator_id
        # Tạo lại đối tượng ClinicCreate từ dict
        clinic_data = ClinicCreate(**clinic_dict)
    
    # Tạo phòng khám mới
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

async def search_clinics(search_term: str, skip: int = 0, limit: int = 100, db: Session = None) -> Tuple[List[Dict[str, Any]], int]:
    """
    Tìm kiếm phòng khám theo tên, mô tả hoặc địa chỉ
    
    Returns:
        Tuple[List[Dict[str, Any]], int]: Danh sách phòng khám và tổng số records
    """
    clinics = get_clinics_by_search(search_term, skip, limit, include_deleted=False, db=db)
    total = count_clinics_by_search(search_term, include_deleted=False, db=db)
    
    # Trả về danh sách đã bao gồm thông tin hình ảnh
    result = []
    for clinic in clinics:
        # Loại bỏ _sa_instance_state
        clinic_dict = {k: v for k, v in clinic.__dict__.items() if k != "_sa_instance_state"}
        
        # Lấy các hình ảnh liên quan
        try:
            from app.services import image_management_service
            images = await image_management_service.get_images_for_object("clinic", clinic.id, db)
            clinic_dict["images"] = images
        except Exception as e:
            clinic_dict["images"] = []
        
        result.append(clinic_dict)
    
    return result, total 