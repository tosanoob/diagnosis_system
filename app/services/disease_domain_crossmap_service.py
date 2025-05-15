"""
Service xử lý logic cho ánh xạ giữa các bệnh thuộc các domain khác nhau
"""
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db import crud
from app.models.database import DiseaseDomainCrossmapCreate, DiseaseDomainCrossmapUpdate

async def get_all_crossmaps(
    skip: int = 0,
    limit: int = 100,
    include_deleted: bool = False,
    db: Session = None
) -> List[Dict[str, Any]]:
    """Lấy danh sách tất cả các ánh xạ giữa các bệnh"""
    crossmaps = crud.disease_domain_crossmap.get_all(db, skip=skip, limit=limit)
    
    result = []
    for crossmap in crossmaps:
        # Loại bỏ _sa_instance_state
        crossmap_dict = {k: v for k, v in crossmap.__dict__.items() if k != "_sa_instance_state"}
        
        # Thêm thông tin domain và disease
        if crossmap.disease_id_1:
            disease_1 = crud.disease.get(db, crossmap.disease_id_1)
            if disease_1:
                disease_dict = {k: v for k, v in disease_1.__dict__.items() if k != "_sa_instance_state"}
                crossmap_dict["disease_1"] = disease_dict
                
        if crossmap.domain_id_1:
            domain_1 = crud.domain.get(db, crossmap.domain_id_1)
            if domain_1:
                domain_dict = {k: v for k, v in domain_1.__dict__.items() if k != "_sa_instance_state"}
                crossmap_dict["domain_1"] = domain_dict
                
        if crossmap.disease_id_2:
            disease_2 = crud.disease.get(db, crossmap.disease_id_2)
            if disease_2:
                disease_dict = {k: v for k, v in disease_2.__dict__.items() if k != "_sa_instance_state"}
                crossmap_dict["disease_2"] = disease_dict
                
        if crossmap.domain_id_2:
            domain_2 = crud.domain.get(db, crossmap.domain_id_2)
            if domain_2:
                domain_dict = {k: v for k, v in domain_2.__dict__.items() if k != "_sa_instance_state"}
                crossmap_dict["domain_2"] = domain_dict
        
        result.append(crossmap_dict)
    
    return result

async def get_crossmap_by_id(crossmap_id: str, db: Session) -> Dict[str, Any]:
    """Lấy thông tin chi tiết của một ánh xạ"""
    crossmap = crud.disease_domain_crossmap.get(db, id=crossmap_id)
    if not crossmap:
        raise HTTPException(status_code=404, detail="Không tìm thấy ánh xạ")
    
    # Loại bỏ _sa_instance_state
    result = {k: v for k, v in crossmap.__dict__.items() if k != "_sa_instance_state"}
    
    # Thêm thông tin domain và disease
    if crossmap.disease_id_1:
        disease_1 = crud.disease.get(db, crossmap.disease_id_1)
        if disease_1:
            disease_dict = {k: v for k, v in disease_1.__dict__.items() if k != "_sa_instance_state"}
            result["disease_1"] = disease_dict
            
    if crossmap.domain_id_1:
        domain_1 = crud.domain.get(db, crossmap.domain_id_1)
        if domain_1:
            domain_dict = {k: v for k, v in domain_1.__dict__.items() if k != "_sa_instance_state"}
            result["domain_1"] = domain_dict
            
    if crossmap.disease_id_2:
        disease_2 = crud.disease.get(db, crossmap.disease_id_2)
        if disease_2:
            disease_dict = {k: v for k, v in disease_2.__dict__.items() if k != "_sa_instance_state"}
            result["disease_2"] = disease_dict
            
    if crossmap.domain_id_2:
        domain_2 = crud.domain.get(db, crossmap.domain_id_2)
        if domain_2:
            domain_dict = {k: v for k, v in domain_2.__dict__.items() if k != "_sa_instance_state"}
            result["domain_2"] = domain_dict
    
    return result

async def get_crossmaps_for_disease(
    disease_id: str, 
    domain_id: str, 
    db: Session
) -> List[Dict[str, Any]]:
    """Lấy danh sách các ánh xạ cho một bệnh và domain cụ thể"""
    crossmaps = crud.disease_domain_crossmap.get_mappings_for_disease(db, disease_id, domain_id)
    
    result = []
    for crossmap in crossmaps:
        # Loại bỏ _sa_instance_state
        crossmap_dict = {k: v for k, v in crossmap.__dict__.items() if k != "_sa_instance_state"}
        
        # Xác định disease và domain được ánh xạ tới
        target_disease_id = crossmap.disease_id_1 if crossmap.disease_id_2 == disease_id and crossmap.domain_id_2 == domain_id else crossmap.disease_id_2
        target_domain_id = crossmap.domain_id_1 if crossmap.domain_id_2 == domain_id else crossmap.domain_id_2
        
        # Thêm thông tin domain và disease đích
        target_disease = crud.disease.get(db, target_disease_id)
        if target_disease:
            disease_dict = {k: v for k, v in target_disease.__dict__.items() if k != "_sa_instance_state"}
            crossmap_dict["target_disease"] = disease_dict
            
        target_domain = crud.domain.get(db, target_domain_id)
        if target_domain:
            domain_dict = {k: v for k, v in target_domain.__dict__.items() if k != "_sa_instance_state"}
            crossmap_dict["target_domain"] = domain_dict
        
        result.append(crossmap_dict)
    
    return result

async def create_crossmap(
    crossmap_data: DiseaseDomainCrossmapCreate, 
    db: Session,
    created_by: Optional[str] = None
) -> Dict[str, Any]:
    """Tạo một ánh xạ mới giữa hai bệnh thuộc hai domain khác nhau"""
    # Kiểm tra xem các disease và domain có tồn tại không
    disease_1 = crud.disease.get(db, id=crossmap_data.disease_id_1)
    if not disease_1 or disease_1.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Bệnh thứ nhất không tồn tại hoặc đã bị xóa")
    
    domain_1 = crud.domain.get(db, id=crossmap_data.domain_id_1)
    if not domain_1 or domain_1.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Domain thứ nhất không tồn tại hoặc đã bị xóa")
        
    disease_2 = crud.disease.get(db, id=crossmap_data.disease_id_2)
    if not disease_2 or disease_2.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Bệnh thứ hai không tồn tại hoặc đã bị xóa")
    
    domain_2 = crud.domain.get(db, id=crossmap_data.domain_id_2)
    if not domain_2 or domain_2.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Domain thứ hai không tồn tại hoặc đã bị xóa")
    
    # Kiểm tra xem disease có thuộc domain không
    if disease_1.domain_id != crossmap_data.domain_id_1:
        raise HTTPException(status_code=400, detail="Bệnh thứ nhất không thuộc domain thứ nhất")
        
    if disease_2.domain_id != crossmap_data.domain_id_2:
        raise HTTPException(status_code=400, detail="Bệnh thứ hai không thuộc domain thứ hai")
    
    # Kiểm tra xem ánh xạ đã tồn tại chưa
    existing_crossmap = crud.disease_domain_crossmap.get_by_disease_and_domain(
        db, 
        crossmap_data.disease_id_1, 
        crossmap_data.domain_id_1,
        crossmap_data.disease_id_2,
        crossmap_data.domain_id_2
    )
    
    if existing_crossmap:
        raise HTTPException(status_code=400, detail="Ánh xạ này đã tồn tại")
    
    # Tạo ánh xạ mới
    crossmap = crud.disease_domain_crossmap.create(db, obj_in=crossmap_data)
    
    # Trả về đầy đủ thông tin
    return await get_crossmap_by_id(crossmap.id, db)

async def update_crossmap(
    crossmap_id: str, 
    crossmap_data: DiseaseDomainCrossmapUpdate, 
    db: Session,
    updated_by: Optional[str] = None
) -> Dict[str, Any]:
    """Cập nhật thông tin ánh xạ"""
    crossmap = crud.disease_domain_crossmap.get(db, id=crossmap_id)
    if not crossmap:
        raise HTTPException(status_code=404, detail="Không tìm thấy ánh xạ")
    
    # Kiểm tra các disease và domain nếu được cập nhật
    if crossmap_data.disease_id_1:
        disease_1 = crud.disease.get(db, id=crossmap_data.disease_id_1)
        if not disease_1 or disease_1.deleted_at is not None:
            raise HTTPException(status_code=404, detail="Bệnh thứ nhất không tồn tại hoặc đã bị xóa")
    
    if crossmap_data.domain_id_1:
        domain_1 = crud.domain.get(db, id=crossmap_data.domain_id_1)
        if not domain_1 or domain_1.deleted_at is not None:
            raise HTTPException(status_code=404, detail="Domain thứ nhất không tồn tại hoặc đã bị xóa")
            
    if crossmap_data.disease_id_2:
        disease_2 = crud.disease.get(db, id=crossmap_data.disease_id_2)
        if not disease_2 or disease_2.deleted_at is not None:
            raise HTTPException(status_code=404, detail="Bệnh thứ hai không tồn tại hoặc đã bị xóa")
    
    if crossmap_data.domain_id_2:
        domain_2 = crud.domain.get(db, id=crossmap_data.domain_id_2)
        if not domain_2 or domain_2.deleted_at is not None:
            raise HTTPException(status_code=404, detail="Domain thứ hai không tồn tại hoặc đã bị xóa")
    
    # Kiểm tra xem disease có thuộc domain không (nếu cả hai được cập nhật)
    if crossmap_data.disease_id_1 and crossmap_data.domain_id_1:
        disease_1 = crud.disease.get(db, id=crossmap_data.disease_id_1)
        if disease_1.domain_id != crossmap_data.domain_id_1:
            raise HTTPException(status_code=400, detail="Bệnh thứ nhất không thuộc domain thứ nhất")
            
    if crossmap_data.disease_id_2 and crossmap_data.domain_id_2:
        disease_2 = crud.disease.get(db, id=crossmap_data.disease_id_2)
        if disease_2.domain_id != crossmap_data.domain_id_2:
            raise HTTPException(status_code=400, detail="Bệnh thứ hai không thuộc domain thứ hai")
    
    # Cập nhật ánh xạ
    updated_crossmap = crud.disease_domain_crossmap.update(db, db_obj=crossmap, obj_in=crossmap_data)
    
    # Trả về đầy đủ thông tin
    return await get_crossmap_by_id(updated_crossmap.id, db)

async def delete_crossmap(
    crossmap_id: str, 
    db: Session
) -> Dict[str, Any]:
    """Xóa một ánh xạ"""
    crossmap = crud.disease_domain_crossmap.get(db, id=crossmap_id)
    if not crossmap:
        raise HTTPException(status_code=404, detail="Không tìm thấy ánh xạ")
    
    # Xóa ánh xạ (hard delete vì không có trường deleted_at)
    deleted_crossmap = crud.disease_domain_crossmap.remove(db, id=crossmap_id)
    
    return {"success": True, "message": "Đã xóa ánh xạ thành công", "id": crossmap_id}

async def get_diseases_by_domain_simple(
    domain_id: str,
    skip: int = 0,
    limit: int = 100,
    include_deleted: bool = False,
    db: Session = None
) -> List[Dict[str, Any]]:
    """Lấy danh sách đơn giản các bệnh thuộc một domain (chỉ gồm id và label)"""
    query = db.query(crud.disease.model).filter(
        crud.disease.model.domain_id == domain_id
    )
    
    if not include_deleted:
        query = query.filter(crud.disease.model.deleted_at.is_(None))
        
    diseases = query.offset(skip).limit(limit).all()
    
    result = []
    for disease in diseases:
        result.append({
            "id": disease.id,
            "label": disease.label,
            "domain_id": disease.domain_id
        })
    
    return result

async def create_crossmaps_batch(
    crossmaps_data: List[DiseaseDomainCrossmapCreate], 
    db: Session,
    created_by: Optional[str] = None
) -> Dict[str, Any]:
    """Tạo nhiều ánh xạ cùng lúc"""
    results = {
        "success": [],
        "failed": []
    }
    
    for idx, crossmap_data in enumerate(crossmaps_data):
        try:
            # Kiểm tra xem các disease và domain có tồn tại không
            disease_1 = crud.disease.get(db, id=crossmap_data.disease_id_1)
            if not disease_1 or disease_1.deleted_at is not None:
                raise HTTPException(status_code=404, detail=f"Bệnh thứ nhất không tồn tại hoặc đã bị xóa (item {idx})")
            
            domain_1 = crud.domain.get(db, id=crossmap_data.domain_id_1)
            if not domain_1 or domain_1.deleted_at is not None:
                raise HTTPException(status_code=404, detail=f"Domain thứ nhất không tồn tại hoặc đã bị xóa (item {idx})")
                
            disease_2 = crud.disease.get(db, id=crossmap_data.disease_id_2)
            if not disease_2 or disease_2.deleted_at is not None:
                raise HTTPException(status_code=404, detail=f"Bệnh thứ hai không tồn tại hoặc đã bị xóa (item {idx})")
            
            domain_2 = crud.domain.get(db, id=crossmap_data.domain_id_2)
            if not domain_2 or domain_2.deleted_at is not None:
                raise HTTPException(status_code=404, detail=f"Domain thứ hai không tồn tại hoặc đã bị xóa (item {idx})")
            
            # Kiểm tra xem disease có thuộc domain không
            if disease_1.domain_id != crossmap_data.domain_id_1:
                raise HTTPException(status_code=400, detail=f"Bệnh thứ nhất không thuộc domain thứ nhất (item {idx})")
                
            if disease_2.domain_id != crossmap_data.domain_id_2:
                raise HTTPException(status_code=400, detail=f"Bệnh thứ hai không thuộc domain thứ hai (item {idx})")
            
            # Kiểm tra xem ánh xạ đã tồn tại chưa
            existing_crossmap = crud.disease_domain_crossmap.get_by_disease_and_domain(
                db, 
                crossmap_data.disease_id_1, 
                crossmap_data.domain_id_1,
                crossmap_data.disease_id_2,
                crossmap_data.domain_id_2
            )
            
            if existing_crossmap:
                results["failed"].append({
                    "data": {
                        "disease_id_1": crossmap_data.disease_id_1,
                        "domain_id_1": crossmap_data.domain_id_1,
                        "disease_id_2": crossmap_data.disease_id_2,
                        "domain_id_2": crossmap_data.domain_id_2
                    },
                    "error": "Ánh xạ này đã tồn tại",
                    "index": idx
                })
                continue
            
            # Tạo ánh xạ mới
            crossmap = crud.disease_domain_crossmap.create(db, obj_in=crossmap_data)
            
            # Thông tin cơ bản về ánh xạ đã tạo
            success_item = {
                "id": crossmap.id,
                "disease_id_1": crossmap.disease_id_1,
                "domain_id_1": crossmap.domain_id_1,
                "disease_id_2": crossmap.disease_id_2,
                "domain_id_2": crossmap.domain_id_2,
                "disease_1_label": disease_1.label,
                "disease_2_label": disease_2.label,
                "domain_1_name": domain_1.domain,
                "domain_2_name": domain_2.domain
            }
            
            results["success"].append(success_item)
            
        except HTTPException as e:
            results["failed"].append({
                "data": {
                    "disease_id_1": crossmap_data.disease_id_1,
                    "domain_id_1": crossmap_data.domain_id_1,
                    "disease_id_2": crossmap_data.disease_id_2,
                    "domain_id_2": crossmap_data.domain_id_2
                },
                "error": e.detail,
                "index": idx
            })
        except Exception as e:
            results["failed"].append({
                "data": {
                    "disease_id_1": crossmap_data.disease_id_1,
                    "domain_id_1": crossmap_data.domain_id_1,
                    "disease_id_2": crossmap_data.disease_id_2,
                    "domain_id_2": crossmap_data.domain_id_2
                },
                "error": str(e),
                "index": idx
            })
    
    return {
        "total": len(crossmaps_data),
        "success_count": len(results["success"]),
        "failed_count": len(results["failed"]),
        "results": results
    } 