from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from sqlalchemy.orm import Session

from app.db.sqlite_service import get_db
from app.services import disease_service
from app.models.database import Disease, DiseaseCreate, DiseaseUpdate
from app.api.routes.auth import get_current_user

router = APIRouter()

@router.get("/", response_model=List[Dict[str, Any]])
async def get_diseases(
    skip: int = 0, 
    limit: int = 100,
    active_only: bool = True,
    domain_id: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách các bệnh
    """
    return await disease_service.get_all_diseases(
        skip=skip,
        limit=limit,
        active_only=active_only,
        domain_id=domain_id,
        search=search,
        db=db
    )

@router.post("/", response_model=Dict[str, Any])
async def create_disease(
    disease: DiseaseCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Tạo bệnh mới
    """
    return await disease_service.create_disease(
        disease_data=disease, 
        db=db,
        created_by=current_user["user_id"]
    )

@router.get("/{disease_id}", response_model=Dict[str, Any])
async def get_disease(
    disease_id: str = Path(..., description="ID của bệnh"),
    db: Session = Depends(get_db)
):
    """
    Lấy thông tin chi tiết của một bệnh
    """
    disease_data = await disease_service.get_disease_by_id(disease_id=disease_id, db=db)
    if disease_data.get("deleted_at"):
        raise HTTPException(status_code=404, detail="Không tìm thấy bệnh này hoặc đã bị xóa")
    return disease_data

@router.put("/{disease_id}", response_model=Dict[str, Any])
async def update_disease(
    disease_id: str = Path(..., description="ID của bệnh"),
    disease: DiseaseUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Cập nhật thông tin bệnh
    """
    return await disease_service.update_disease(
        disease_id=disease_id,
        disease_data=disease,
        db=db,
        updated_by=current_user["user_id"]
    )

@router.delete("/{disease_id}", response_model=Dict[str, Any])
async def delete_disease(
    disease_id: str = Path(..., description="ID của bệnh"),
    soft_delete: bool = True,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Xóa bệnh (mặc định là soft delete)
    """
    return await disease_service.delete_disease(
        disease_id=disease_id,
        soft_delete=soft_delete,
        deleted_by=current_user["user_id"],
        db=db
    )

@router.get("/domain/{domain_id}", response_model=List[Dict[str, Any]])
async def get_diseases_by_domain(
    domain_id: str = Path(..., description="ID của domain"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách các bệnh theo domain
    """
    return await disease_service.get_disease_by_domain(
        domain_id=domain_id,
        skip=skip,
        limit=limit,
        db=db
    )

@router.get("/search/{search_term}", response_model=List[Dict[str, Any]])
async def search_diseases(
    search_term: str = Path(..., description="Từ khóa tìm kiếm"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Tìm kiếm bệnh theo tên hoặc mô tả
    """
    return await disease_service.search_diseases(
        search_term=search_term,
        skip=skip,
        limit=limit,
        db=db
    ) 