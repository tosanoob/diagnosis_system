from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from sqlalchemy.orm import Session

from app.db.sqlite_service import get_db
from app.services import clinic_service
from app.models.database import Clinic, ClinicCreate, ClinicUpdate
from app.api.routes.auth import get_current_user

router = APIRouter()

@router.get("/", response_model=List[Dict[str, Any]])
async def get_clinics(
    skip: int = 0, 
    limit: int = 100,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách các phòng khám
    """
    clinics = await clinic_service.get_all_clinics(
        skip=skip,
        limit=limit,
        search=search,
        db=db
    )
    # Filter out soft-deleted clinics
    return [clinic for clinic in clinics if not clinic.get("deleted_at")]

@router.post("/", response_model=Dict[str, Any])
async def create_clinic(
    clinic: ClinicCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Tạo phòng khám mới
    """
    print(current_user)
    return await clinic_service.create_clinic(
        clinic_data=clinic,
        creator_id=current_user["user_id"],
        db=db
    )

@router.get("/{clinic_id}", response_model=Dict[str, Any])
async def get_clinic(
    clinic_id: str = Path(..., description="ID của phòng khám"),
    db: Session = Depends(get_db)
):
    """
    Lấy thông tin chi tiết của một phòng khám
    """
    clinic_data = await clinic_service.get_clinic_by_id(clinic_id=clinic_id, db=db)
    if clinic_data.get("deleted_at"):
        raise HTTPException(status_code=404, detail="Không tìm thấy phòng khám này hoặc đã bị xóa")
    return clinic_data

@router.put("/{clinic_id}", response_model=Dict[str, Any])
async def update_clinic(
    clinic_id: str = Path(..., description="ID của phòng khám"),
    clinic: ClinicUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Cập nhật thông tin phòng khám
    """
    print(current_user)
    return await clinic_service.update_clinic(
        clinic_id=clinic_id,
        clinic_data=clinic,
        updater_id=current_user["user_id"],
        db=db
    )

@router.delete("/{clinic_id}", response_model=Dict[str, Any])
async def delete_clinic(
    clinic_id: str = Path(..., description="ID của phòng khám"),
    soft_delete: bool = True,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Xóa phòng khám (mặc định là soft delete)
    """
    return await clinic_service.delete_clinic(
        clinic_id=clinic_id,
        soft_delete=soft_delete,
        deleted_by=current_user["user_id"],
        db=db
    )

@router.get("/search/{search_term}", response_model=List[Dict[str, Any]])
async def search_clinics(
    search_term: str = Path(..., description="Từ khóa tìm kiếm"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Tìm kiếm phòng khám theo tên, mô tả hoặc địa chỉ
    """
    clinics = await clinic_service.search_clinics(
        search_term=search_term,
        skip=skip,
        limit=limit,
        db=db
    )
    # Filter out soft-deleted clinics
    return [clinic for clinic in clinics if not clinic.get("deleted_at")] 