"""
Service xử lý logic cho domain
"""
from typing import List, Dict, Any, Optional, Tuple
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.db import crud
from app.models.database import DomainCreate, DomainUpdate

async def get_all_domains(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    include_deleted: bool = False,
    db: Session = None
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Lấy danh sách các domain
    
    Returns:
        Tuple[List[Dict[str, Any]], int]: Danh sách domain và tổng số records
    """
    if search:
        domains = get_domains_by_search(search, skip, limit, include_deleted, db)
        total = count_domains_by_search(search, include_deleted, db)
    else:
        domains = get_all_domains_base(skip, limit, include_deleted, db)
        total = count_all_domains(include_deleted, db)
    
    # Chuyển domain thành dicts phù hợp với JSON
    result = []
    for domain in domains:
        # Loại bỏ _sa_instance_state
        domain_dict = {k: v for k, v in domain.__dict__.items() if k != "_sa_instance_state"}
        result.append(domain_dict)
    
    return result, total

def get_domains_by_search(search_term: str, skip: int, limit: int, include_deleted: bool, db: Session):
    """Helper function để tìm kiếm domain"""
    search_pattern = f"%{search_term}%"
    query = db.query(crud.domain.model).filter(
        or_(
            crud.domain.model.domain.ilike(search_pattern),
            crud.domain.model.description.ilike(search_pattern)
        )
    )
    
    if not include_deleted:
        query = query.filter(crud.domain.model.deleted_at.is_(None))
        
    return query.offset(skip).limit(limit).all()

def get_all_domains_base(skip: int, limit: int, include_deleted: bool, db: Session):
    """Helper function để lấy tất cả domain"""
    query = db.query(crud.domain.model)
    
    if not include_deleted:
        query = query.filter(crud.domain.model.deleted_at.is_(None))
        
    return query.offset(skip).limit(limit).all()

def count_domains_by_search(search_term: str, include_deleted: bool, db: Session) -> int:
    """Helper function để đếm domain theo kết quả tìm kiếm"""
    search_pattern = f"%{search_term}%"
    query = db.query(func.count(crud.domain.model.id)).filter(
        or_(
            crud.domain.model.domain.ilike(search_pattern),
            crud.domain.model.description.ilike(search_pattern)
        )
    )
    
    if not include_deleted:
        query = query.filter(crud.domain.model.deleted_at.is_(None))
        
    return query.scalar()

def count_all_domains(include_deleted: bool, db: Session) -> int:
    """Helper function để đếm tất cả domain"""
    query = db.query(func.count(crud.domain.model.id))
    
    if not include_deleted:
        query = query.filter(crud.domain.model.deleted_at.is_(None))
        
    return query.scalar()

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
    """Xóa domain và tất cả các bệnh thuộc domain đó"""
    domain = crud.domain.get(db, id=domain_id)
    if not domain:
        raise HTTPException(status_code=404, detail="Không tìm thấy domain")
    
    if domain.deleted_at is not None:
        raise HTTPException(status_code=400, detail="Domain đã bị xóa trước đó")
    
    # Lấy tất cả các bệnh thuộc domain này
    diseases = db.query(crud.disease.model).filter(
        crud.disease.model.domain_id == domain_id,
        crud.disease.model.deleted_at.is_(None)
    ).all()
    
    # Xóa tất cả các bệnh thuộc domain
    for disease in diseases:
        if soft_delete:
            crud.disease.soft_delete(db, id=disease.id, deleted_by=deleted_by)
        else:
            crud.disease.remove(db, id=disease.id)
    
    # Xóa domain
    if soft_delete:
        deleted_domain = crud.domain.soft_delete(db, id=domain_id, deleted_by=deleted_by)
    else:
        deleted_domain = crud.domain.remove(db, id=domain_id)
    
    # Trả về một dict sạch không chứa _sa_instance_state
    result = {k: v for k, v in deleted_domain.__dict__.items() if k != "_sa_instance_state"}
    result["diseases_deleted"] = len(diseases)
    return result

async def search_domains(search_term: str, skip: int = 0, limit: int = 100, include_deleted: bool = False, db: Session = None) -> Tuple[List[Dict[str, Any]], int]:
    """
    Tìm kiếm domain theo tên hoặc mô tả
    
    Returns:
        Tuple[List[Dict[str, Any]], int]: Danh sách domain và tổng số records
    """
    domains = get_domains_by_search(search_term, skip, limit, include_deleted, db)
    total = count_domains_by_search(search_term, include_deleted, db)
    
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
    
    return result, total 