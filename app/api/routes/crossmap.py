from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from sqlalchemy.orm import Session

from app.db.sqlite_service import get_db
from app.services import disease_domain_crossmap_service
from app.models.database import DiseaseDomainCrossmapCreate, DiseaseDomainCrossmapUpdate, DiseaseDomainCrossmapBatchCreate
from app.api.routes.auth import get_current_user, get_admin_user

router = APIRouter()

@router.get("", response_model=List[Dict[str, Any]])
async def get_all_crossmaps(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Lấy danh sách tất cả các ánh xạ giữa các bệnh
    """
    return await disease_domain_crossmap_service.get_all_crossmaps(
        skip=skip,
        limit=limit,
        db=db
    )

@router.post("", response_model=Dict[str, Any])
async def create_crossmap(
    crossmap: DiseaseDomainCrossmapCreate = Body(...),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_admin_user)  # Chỉ admin mới được tạo ánh xạ
):
    """
    Tạo ánh xạ mới giữa hai bệnh thuộc hai domain khác nhau
    """
    return await disease_domain_crossmap_service.create_crossmap(
        crossmap_data=crossmap,
        db=db,
        created_by=current_user["user_id"]
    )

@router.get("/{crossmap_id}", response_model=Dict[str, Any])
async def get_crossmap(
    crossmap_id: str = Path(..., description="ID của ánh xạ"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Lấy thông tin chi tiết của một ánh xạ
    """
    return await disease_domain_crossmap_service.get_crossmap_by_id(
        crossmap_id=crossmap_id,
        db=db
    )

@router.put("/{crossmap_id}", response_model=Dict[str, Any])
async def update_crossmap(
    crossmap_id: str = Path(..., description="ID của ánh xạ"),
    crossmap: DiseaseDomainCrossmapUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_admin_user)  # Chỉ admin mới được cập nhật ánh xạ
):
    """
    Cập nhật thông tin ánh xạ
    """
    return await disease_domain_crossmap_service.update_crossmap(
        crossmap_id=crossmap_id,
        crossmap_data=crossmap,
        db=db,
        updated_by=current_user["user_id"]
    )

@router.delete("/{crossmap_id}", response_model=Dict[str, Any])
async def delete_crossmap(
    crossmap_id: str = Path(..., description="ID của ánh xạ"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_admin_user)  # Chỉ admin mới được xóa ánh xạ
):
    """
    Xóa ánh xạ
    """
    return await disease_domain_crossmap_service.delete_crossmap(
        crossmap_id=crossmap_id,
        db=db
    )

@router.get("/disease/{disease_id}/domain/{domain_id}", response_model=List[Dict[str, Any]])
async def get_crossmaps_for_disease(
    disease_id: str = Path(..., description="ID của bệnh"),
    domain_id: str = Path(..., description="ID của domain"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Lấy danh sách các ánh xạ cho một bệnh và domain cụ thể
    """
    return await disease_domain_crossmap_service.get_crossmaps_for_disease(
        disease_id=disease_id,
        domain_id=domain_id,
        db=db
    )

@router.get("/domain/{domain_id}/diseases", response_model=List[Dict[str, Any]])
async def get_diseases_by_domain_simple(
    domain_id: str = Path(..., description="ID của domain"),
    skip: int = 0,
    limit: int = 100,
    include_deleted: bool = False,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Lấy danh sách đơn giản các bệnh thuộc một domain (chỉ gồm id và label)
    """
    # Nếu không phải admin và muốn xem cả những record đã xóa
    if include_deleted and current_user.get("role", "").lower() != "admin":
        include_deleted = False
        
    return await disease_domain_crossmap_service.get_diseases_by_domain_simple(
        domain_id=domain_id,
        skip=skip,
        limit=limit,
        include_deleted=include_deleted,
        db=db
    )

@router.post("/batch", response_model=Dict[str, Any])
async def create_crossmaps_batch(
    batch_data: DiseaseDomainCrossmapBatchCreate = Body(...),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_admin_user)  # Chỉ admin mới được tạo hàng loạt ánh xạ
):
    """
    Tạo nhiều ánh xạ cùng lúc
    """
    return await disease_domain_crossmap_service.create_crossmaps_batch(
        crossmaps_data=batch_data.crossmaps,
        db=db,
        created_by=current_user["user_id"]
    ) 