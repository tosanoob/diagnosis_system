from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from sqlalchemy.orm import Session

from app.db.sqlite_service import get_db
from app.services import disease_domain_crossmap_service
from app.db import crud
from app.models.database import DiseaseDomainCrossmapCreate, DiseaseDomainCrossmapUpdate, DiseaseDomainCrossmapBatchCreate, StandardDomainCrossmapBatchUpdate, CrossmapImportRequest
from app.api.routes.auth import get_current_user, get_admin_user
from app.core.logging import logger

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

@router.post("/batch/standard", response_model=Dict[str, Any])
async def batch_update_standard_domain_crossmaps(
    batch_data: StandardDomainCrossmapBatchUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_admin_user)  # Chỉ admin mới được tạo hàng loạt ánh xạ
):
    """
    Tạo batch ánh xạ từ domain STANDARD sang domain khác, 
    xóa tất cả ánh xạ cũ và tạo mới, đồng thời cập nhật vectordb
    """
    return await disease_domain_crossmap_service.batch_update_standard_domain_crossmaps(
        target_domain_id=batch_data.target_domain_id,
        crossmaps_lite=batch_data.crossmaps_lite,
        db=db,
        created_by=current_user["user_id"]
    )

@router.get("/domains/{domain_id1}/{domain_id2}", response_model=Dict[str, Any])
async def get_crossmaps_between_domains(
    domain_id1: str = Path(..., description="ID của domain thứ nhất"),
    domain_id2: str = Path(..., description="ID của domain thứ hai"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Lấy danh sách các cặp ánh xạ giữa các bệnh từ 2 domain.
    Trả về danh sách đầy đủ để client-side có thể tạo ra định dạng export phù hợp.
    
    Trả về:
    - Thông tin về các domain
    - Danh sách các ánh xạ giữa các bệnh, được nhóm theo bệnh domain đích
    """
    crossmaps = await disease_domain_crossmap_service.get_crossmaps_between_domains(
        domain_id1=domain_id1,
        domain_id2=domain_id2,
        db=db
    )
    
    # Thêm thông tin về domain
    domain1 = crud.domain.get(db, domain_id1)
    domain2 = crud.domain.get(db, domain_id2)
    
    # Chuyển đổi dữ liệu để client-side dễ dàng tạo export format
    result_by_target = {}
    
    for crossmap in crossmaps:
        source_disease_id = crossmap.get("source_disease_id")
        source_disease_label = crossmap.get("source_disease_label")
        target_disease_id = crossmap.get("target_disease_id")
        target_disease_label = crossmap.get("target_disease_label")
        
        # Nhóm theo target disease
        if target_disease_id not in result_by_target:
            result_by_target[target_disease_id] = {
                "target_disease_id": target_disease_id,
                "target_disease_label": target_disease_label,
                "source_diseases": []
            }
        
        result_by_target[target_disease_id]["source_diseases"].append({
            "source_disease_id": source_disease_id,
            "source_disease_label": source_disease_label,
            "crossmap_id": crossmap.get("crossmap_id")
        })
    
    return {
        "domain1": {
            "id": domain_id1,
            "name": domain1.domain if domain1 else "Unknown"
        },
        "domain2": {
            "id": domain_id2,
            "name": domain2.domain if domain2 else "Unknown"
        },
        "crossmaps": list(result_by_target.values()),
        "total_target_diseases": len(result_by_target),
        "total_crossmaps": len(crossmaps)
    }

@router.post("/import", response_model=Dict[str, Any])
async def import_crossmaps_from_json(
    import_data: CrossmapImportRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_admin_user)  # Chỉ admin mới được import
):
    """
    Import ánh xạ từ JSON format.
    Nhận vào tên domain đích và một JSON mapping.
    Hỗ trợ cả định dạng đơn nhãn: {'tên bệnh domain đích': 'tên bệnh STANDARD'} 
    và đa nhãn: {'tên bệnh domain đích': ['tên bệnh STANDARD 1', 'tên bệnh STANDARD 2']}.
    Sử dụng fuzzy matching để tìm tên bệnh chính xác và xóa sạch ánh xạ cũ trước khi tạo mới.
    """
    logger.app_info(f"Nhận yêu cầu import crossmaps cho domain: {import_data.target_domain_name}")
    
    return await disease_domain_crossmap_service.import_crossmaps_from_json(
        target_domain_name=import_data.target_domain_name,
        mappings=import_data.mappings,
        db=db,
        created_by=current_user["user_id"]
    ) 