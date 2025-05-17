from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from sqlalchemy.orm import Session

from app.db.sqlite_service import get_db
from app.services import domain_service
from app.models.database import Domain, DomainCreate, DomainUpdate
from app.models.response import PaginatedResponse
from app.api.routes.auth import get_current_user, get_admin_user, get_optional_user

router = APIRouter()

@router.get("", response_model=Dict[str, Any])
async def get_domains(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None, 
    include_deleted: bool = False,
    db: Session = Depends(get_db),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """
    Lấy danh sách các domain với phân trang
    """
    # Nếu không có token hoặc không phải admin và muốn xem cả những record đã xóa
    if include_deleted and (not current_user or current_user.get("role", "").lower() != "admin"):
        include_deleted = False
    
    items, total = await domain_service.get_all_domains(
        skip=skip,
        limit=limit,
        search=search,
        include_deleted=include_deleted,
        db=db
    )
    
    return PaginatedResponse.create(items, total, skip, limit)

@router.post("", response_model=Dict[str, Any])
async def create_domain(
    domain: DomainCreate = Body(...),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_admin_user)  # Chỉ admin mới được tạo domain
):
    """
    Tạo lĩnh vực y tế mới
    """
    return await domain_service.create_domain(
        domain_data=domain,
        db=db,
        created_by=current_user["user_id"]
    )

@router.get("/{domain_id}", response_model=Dict[str, Any])
async def get_domain(
    domain_id: str = Path(..., description="ID của lĩnh vực y tế"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Lấy thông tin chi tiết của một lĩnh vực y tế
    """
    domain = await domain_service.get_domain_by_id(domain_id=domain_id, db=db)
    
    # Nếu domain đã bị xóa, chỉ admin mới được xem
    if domain.get("deleted_at") and current_user.get("role", "").lower() != "admin":
        raise HTTPException(status_code=404, detail="Không tìm thấy lĩnh vực y tế")
        
    return domain

@router.put("/{domain_id}", response_model=Dict[str, Any])
async def update_domain(
    domain_id: str = Path(..., description="ID của lĩnh vực y tế"),
    domain: DomainUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_admin_user)  # Chỉ admin mới được cập nhật domain
):
    """
    Cập nhật thông tin lĩnh vực y tế
    """
    return await domain_service.update_domain(
        domain_id=domain_id,
        domain_data=domain,
        db=db,
        updated_by=current_user["user_id"]
    )

@router.delete("/{domain_id}", response_model=Dict[str, Any])
async def delete_domain(
    domain_id: str = Path(..., description="ID của lĩnh vực y tế"),
    soft_delete: bool = True,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_admin_user)  # Chỉ admin mới được xóa domain
):
    """
    Xóa lĩnh vực y tế (mặc định là soft delete)
    """
    return await domain_service.delete_domain(
        domain_id=domain_id,
        soft_delete=soft_delete,
        deleted_by=current_user["user_id"],
        db=db
    )

@router.get("/search/{search_term}", response_model=Dict[str, Any])
async def search_domains(
    search_term: str = Path(..., description="Từ khóa tìm kiếm"),
    skip: int = 0,
    limit: int = 100,
    include_deleted: bool = False,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Tìm kiếm lĩnh vực y tế theo tên hoặc mô tả với phân trang
    """
    # Nếu không phải admin và muốn xem cả những record đã xóa
    if include_deleted and current_user.get("role", "").lower() != "admin":
        include_deleted = False
    
    items, total = await domain_service.search_domains(
        search_term=search_term,
        skip=skip,
        limit=limit,
        include_deleted=include_deleted,
        db=db
    )
    
    return PaginatedResponse.create(items, total, skip, limit)
