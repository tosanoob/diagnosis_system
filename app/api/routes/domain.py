from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session

from app.db.sqlite_service import get_db
from app.db import crud
from app.models.database import Domain, DomainCreate, DomainUpdate
from app.api.routes.auth import get_current_user

router = APIRouter()

@router.get("", response_model=List[Domain])
def get_domains(
    skip: int = 0, 
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách các lĩnh vực y tế
    """
    # Chỉ lấy các domain chưa bị xóa (soft delete)
    domains = db.query(crud.domain.model).filter(
        crud.domain.model.deleted_at.is_(None)
    ).offset(skip).limit(limit).all()

    return domains

@router.post("", response_model=Domain)
def create_domain(
    domain: DomainCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Tạo lĩnh vực y tế mới
    """
    # Lấy user_id từ token để gán cho created_by
    domain.created_by = current_user["user_id"]
    
    return crud.domain.create(db, obj_in=domain)

@router.get("/{domain_id}", response_model=Domain)
def get_domain(
    domain_id: str = Path(..., description="ID của lĩnh vực y tế"),
    db: Session = Depends(get_db)
):
    """
    Lấy thông tin chi tiết của một lĩnh vực y tế
    """
    db_domain = crud.domain.get(db, id=domain_id)
    if db_domain is None or db_domain.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Không tìm thấy lĩnh vực y tế")
    return db_domain

@router.put("/{domain_id}", response_model=Domain)
def update_domain(
    domain_id: str = Path(..., description="ID của lĩnh vực y tế"),
    domain: DomainUpdate = None,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Cập nhật thông tin lĩnh vực y tế
    """
    db_domain = crud.domain.get(db, id=domain_id)
    if db_domain is None or db_domain.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Không tìm thấy lĩnh vực y tế")
    
    # Thêm thông tin người cập nhật từ token
    if domain:
        domain.updated_by = current_user["user_id"]
        
    return crud.domain.update(db, db_obj=db_domain, obj_in=domain)

@router.delete("/{domain_id}", response_model=Domain)
def delete_domain(
    domain_id: str = Path(..., description="ID của lĩnh vực y tế"),
    db: Session = Depends(get_db),
    soft_delete: bool = True,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Xóa lĩnh vực y tế (mặc định là soft delete)
    """
    db_domain = crud.domain.get(db, id=domain_id)
    if db_domain is None or db_domain.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Không tìm thấy lĩnh vực y tế")
    
    if soft_delete:
        return crud.domain.soft_delete(db, id=domain_id, deleted_by=current_user["user_id"])
    else:
        return crud.domain.remove(db, id=domain_id)
