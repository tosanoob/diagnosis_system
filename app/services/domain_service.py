"""
Service xử lý logic cho domain
"""
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db import crud
from app.models.database import DomainCreate, DomainUpdate

async def get_all_domains(
    skip: int = 0,
    limit: int = 100,
    include_deleted: bool = False,
    db: Session = None
) -> List[Dict[str, Any]]:
    """Lấy danh sách các domain"""
    query = db.query(crud.domain.model)
    
    if not include_deleted:
        query = query.filter(crud.domain.model.deleted_at.is_(None))
        
    domains = query.offset(skip).limit(limit).all()
    
    result = []
    for domain in domains:
        # Loại bỏ _sa_instance_state
        domain_dict = {k: v for k, v in domain.__dict__.items() if k != "_sa_instance_state"}
        result.append(domain_dict)
    
    return result

async def get_domain_by_id(domain_id: str, db: Session) -> Dict[str, Any]:
    """Lấy thông tin chi tiết của một domain"""
    domain = crud.domain.get(db, id=domain_id)
    if not domain:
        raise HTTPException(status_code=404, detail="Không tìm thấy domain")
    
    if domain.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Domain đã bị xóa")
    
    # Loại bỏ _sa_instance_state
    result = {k: v for k, v in domain.__dict__.items() if k != "_sa_instance_state"}
    
    # Lấy số lượng bệnh thuộc domain này
    disease_count = db.query(crud.disease.model).filter(
        crud.disease.model.domain_id == domain_id,
        crud.disease.model.deleted_at.is_(None)
    ).count()
    
    result["disease_count"] = disease_count
    
    return result

async def get_domain_by_name(domain_name: str, db: Session) -> Optional[Dict[str, Any]]:
    """Lấy thông tin domain theo tên"""
    domain = crud.domain.get_by_name(db, domain_name)
    if not domain:
        return None
    
    # Loại bỏ _sa_instance_state
    result = {k: v for k, v in domain.__dict__.items() if k != "_sa_instance_state"}
    
    # Lấy số lượng bệnh thuộc domain này
    disease_count = db.query(crud.disease.model).filter(
        crud.disease.model.domain_id == domain.id,
        crud.disease.model.deleted_at.is_(None)
    ).count()
    
    result["disease_count"] = disease_count
    
    return result

async def create_domain(domain_data: DomainCreate, db: Session, created_by: Optional[str] = None) -> Dict[str, Any]:
    """Tạo một domain mới"""
    # Kiểm tra xem domain đã tồn tại chưa
    existing_domain = crud.domain.get_by_name(db, domain_data.domain)
    if existing_domain and existing_domain.deleted_at is None:
        raise HTTPException(status_code=400, detail="Domain này đã tồn tại")
    
    # Thêm thông tin người tạo
    if created_by:
        domain_dict = domain_data.model_dump()
        domain_dict["created_by"] = created_by
        domain_data = DomainCreate(**domain_dict)
    
    domain = crud.domain.create(db, obj_in=domain_data)
    
    # Trả về một dict sạch không chứa _sa_instance_state
    result = {k: v for k, v in domain.__dict__.items() if k != "_sa_instance_state"}
    return result

async def update_domain(domain_id: str, domain_data: DomainUpdate, db: Session, updated_by: Optional[str] = None) -> Dict[str, Any]:
    """Cập nhật thông tin domain"""
    domain = crud.domain.get(db, id=domain_id)
    if not domain:
        raise HTTPException(status_code=404, detail="Không tìm thấy domain")
    
    if domain.deleted_at is not None:
        raise HTTPException(status_code=400, detail="Không thể cập nhật domain đã bị xóa")
    
    # Kiểm tra xem tên domain mới đã tồn tại chưa (nếu có thay đổi tên)
    if domain_data.domain and domain_data.domain != domain.domain:
        existing_domain = crud.domain.get_by_name(db, domain_data.domain)
        if existing_domain and existing_domain.id != domain_id and existing_domain.deleted_at is None:
            raise HTTPException(status_code=400, detail="Tên domain này đã tồn tại")
    
    # Thêm thông tin người cập nhật
    if updated_by:
        domain_dict = domain_data.model_dump(exclude_unset=True)
        domain_dict["updated_by"] = updated_by
        domain_data = DomainUpdate(**domain_dict)
    
    updated_domain = crud.domain.update(db, db_obj=domain, obj_in=domain_data)
    
    # Trả về một dict sạch không chứa _sa_instance_state
    result = {k: v for k, v in updated_domain.__dict__.items() if k != "_sa_instance_state"}
    return result

async def delete_domain(domain_id: str, soft_delete: bool = True, deleted_by: Optional[str] = None, db: Session = None) -> Dict[str, Any]:
    """Xóa domain"""
    domain = crud.domain.get(db, id=domain_id)
    if not domain:
        raise HTTPException(status_code=404, detail="Không tìm thấy domain")
    
    if domain.deleted_at is not None:
        raise HTTPException(status_code=400, detail="Domain đã bị xóa trước đó")
    
    # Kiểm tra xem có bệnh nào đang sử dụng domain này không
    diseases_count = db.query(crud.disease.model).filter(
        crud.disease.model.domain_id == domain_id,
        crud.disease.model.deleted_at.is_(None)
    ).count()
    
    # Bỏ đoạn validation này để phù hợp với logic xóa dataset
    # Vì khi xóa dataset chúng ta cần xóa cả domain và tất cả bệnh
    # if diseases_count > 0:
    #    raise HTTPException(status_code=400, detail=f"Không thể xóa domain vì có {diseases_count} bệnh đang sử dụng nó")
    
    if soft_delete:
        deleted_domain = crud.domain.soft_delete(db, id=domain_id, deleted_by=deleted_by)
    else:
        deleted_domain = crud.domain.remove(db, id=domain_id)
    
    # Trả về một dict sạch không chứa _sa_instance_state
    result = {k: v for k, v in deleted_domain.__dict__.items() if k != "_sa_instance_state"}
    return result

async def search_domains(search_term: str, skip: int = 0, limit: int = 100, include_deleted: bool = False, db: Session = None) -> List[Dict[str, Any]]:
    """Tìm kiếm domain theo tên hoặc mô tả"""
    search_pattern = f"%{search_term}%"
    query = db.query(crud.domain.model).filter(
        crud.domain.model.domain.ilike(search_pattern) | crud.domain.model.description.ilike(search_pattern)
    )
    
    if not include_deleted:
        query = query.filter(crud.domain.model.deleted_at.is_(None))
        
    domains = query.offset(skip).limit(limit).all()
    
    result = []
    for domain in domains:
        # Loại bỏ _sa_instance_state
        domain_dict = {k: v for k, v in domain.__dict__.items() if k != "_sa_instance_state"}
        
        # Đếm số lượng bệnh trong domain
        disease_count = db.query(crud.disease.model).filter(
            crud.disease.model.domain_id == domain.id,
            crud.disease.model.deleted_at.is_(None)
        ).count()
        
        domain_dict["disease_count"] = disease_count
        result.append(domain_dict)
    
    return result 