"""
Service xử lý logic cho ánh xạ giữa các bệnh thuộc các domain khác nhau
"""
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from rapidfuzz import fuzz, process

from app.db import crud
from app.models.database import DiseaseDomainCrossmapCreate, DiseaseDomainCrossmapUpdate
from app.db.chromadb_service import chromadb_instance
from app.core.logging import logger

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

async def batch_update_standard_domain_crossmaps(
    target_domain_id: str, 
    crossmaps_lite: List[Dict[str, str]], 
    db: Session,
    created_by: Optional[str] = None
) -> Dict[str, Any]:
    """
    Tạo batch ánh xạ từ domain STANDARD sang domain target, xóa tất cả ánh xạ cũ và tạo mới
    
    Args:
        target_domain_id: ID của domain đích
        crossmaps_lite: Danh sách các cặp {"standard_disease_id": "...", "target_disease_id": "..."}
        db: Database session
        created_by: Người tạo ánh xạ
        
    Returns:
        Dict[str, Any]: Kết quả xử lý batch
    """
    # Kiểm tra target domain có tồn tại không
    target_domain = crud.domain.get(db, id=target_domain_id)
    if not target_domain or target_domain.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Domain đích không tồn tại hoặc đã bị xóa")
    
    # Tìm domain STANDARD
    standard_domain = db.query(crud.domain.model).filter(
        crud.domain.model.domain.ilike("STANDARD"),
        crud.domain.model.deleted_at.is_(None)
    ).first()
    
    if not standard_domain:
        raise HTTPException(status_code=404, detail="Không tìm thấy domain STANDARD")
    
    standard_domain_id = standard_domain.id
    
    # Xóa tất cả ánh xạ cũ giữa domain STANDARD và domain target
    existing_crossmaps = db.query(crud.disease_domain_crossmap.model).filter(
        ((crud.disease_domain_crossmap.model.domain_id_1 == standard_domain_id) & 
         (crud.disease_domain_crossmap.model.domain_id_2 == target_domain_id)) | 
        ((crud.disease_domain_crossmap.model.domain_id_1 == target_domain_id) & 
         (crud.disease_domain_crossmap.model.domain_id_2 == standard_domain_id))
    ).all()
    
    # Xóa ánh xạ trong ChromaDB
    for crossmap in existing_crossmaps:
        try:
            # Xác định đâu là domain và disease từ STANDARD
            if crossmap.domain_id_1 == standard_domain_id:
                standard_disease_id = crossmap.disease_id_1
                target_disease_id = crossmap.disease_id_2
            else:
                standard_disease_id = crossmap.disease_id_2
                target_disease_id = crossmap.disease_id_1
            
            # Gọi hàm delete_mapping để xóa trong ChromaDB
            chromadb_instance.delete_mapping(
                domain_id=target_domain_id, 
                domain_disease_id=target_disease_id
            )
        except Exception as e:
            logger.error(f"Lỗi khi xóa ánh xạ từ ChromaDB: {str(e)}")
    
    # Xóa crossmaps trong database
    for crossmap in existing_crossmaps:
        db.delete(crossmap)
    db.commit()
    
    # Tạo các ánh xạ mới
    results = {
        "success": [],
        "failed": []
    }
    
    for idx, crossmap_lite in enumerate(crossmaps_lite):
        try:
            standard_disease_id = crossmap_lite.get("standard_disease_id")
            target_disease_id = crossmap_lite.get("target_disease_id")
            
            if not standard_disease_id or not target_disease_id:
                raise ValueError("Thiếu standard_disease_id hoặc target_disease_id")
                
            # Kiểm tra các disease có tồn tại không
            standard_disease = crud.disease.get(db, id=standard_disease_id)
            target_disease = crud.disease.get(db, id=target_disease_id)
            
            if not standard_disease or standard_disease.deleted_at is not None:
                raise ValueError(f"Bệnh chuẩn (standard_disease_id={standard_disease_id}) không tồn tại hoặc đã bị xóa")
                
            if not target_disease or target_disease.deleted_at is not None:
                raise ValueError(f"Bệnh đích (target_disease_id={target_disease_id}) không tồn tại hoặc đã bị xóa")
            
            # Kiểm tra disease có thuộc domain tương ứng không
            if standard_disease.domain_id != standard_domain_id:
                raise ValueError(f"Bệnh chuẩn (standard_disease_id={standard_disease_id}) không thuộc domain STANDARD")
                
            if target_disease.domain_id != target_domain_id:
                raise ValueError(f"Bệnh đích (target_disease_id={target_disease_id}) không thuộc domain đích")
            
            # Tạo crossmap mới
            crossmap_dict = {
                "disease_id_1": standard_disease_id,
                "domain_id_1": standard_domain_id,
                "disease_id_2": target_disease_id,
                "domain_id_2": target_domain_id
            }
            
            # Thêm trường created_by vào dict nếu có
            if created_by:
                crossmap_dict["created_by"] = created_by
                
            # Tạo model từ dict
            crossmap_data = DiseaseDomainCrossmapCreate(**crossmap_dict)
                
            new_crossmap = crud.disease_domain_crossmap.create(db, obj_in=crossmap_data)
            
            # Tạo ánh xạ trong ChromaDB
            try:
                chromadb_instance.create_mapping(
                    domain_id=target_domain_id,
                    domain_disease_id=target_disease_id,
                    label_id=standard_disease_id,
                    label=standard_disease.label
                )
            except Exception as e:
                import traceback
                print(traceback.format_exc())
                logger.error(f"Lỗi khi tạo ánh xạ trong ChromaDB: {str(e)}")
            
            # Thêm vào kết quả thành công
            results["success"].append({
                "id": new_crossmap.id,
                "standard_disease_id": standard_disease_id,
                "standard_disease_label": standard_disease.label,
                "target_disease_id": target_disease_id,
                "target_disease_label": target_disease.label
            })
            
        except Exception as e:
            # Thêm vào kết quả thất bại
            results["failed"].append({
                "data": crossmap_lite,
                "error": str(e),
                "index": idx
            })
    
    return {
        "total": len(crossmaps_lite),
        "success_count": len(results["success"]),
        "failed_count": len(results["failed"]),
        "target_domain_id": target_domain_id,
        "target_domain_name": target_domain.domain,
        "standard_domain_id": standard_domain_id,
        "standard_domain_name": standard_domain.domain,
        "results": results
    }

async def get_crossmaps_between_domains(
    domain_id1: str,
    domain_id2: str,
    db: Session
) -> List[Dict[str, Any]]:
    """Lấy danh sách các ánh xạ giữa hai domain"""
    # Kiểm tra xem cả hai domain có tồn tại không
    domain_1 = crud.domain.get(db, id=domain_id1)
    if not domain_1 or domain_1.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Domain thứ nhất không tồn tại hoặc đã bị xóa")
        
    domain_2 = crud.domain.get(db, id=domain_id2)
    if not domain_2 or domain_2.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Domain thứ hai không tồn tại hoặc đã bị xóa")
    
    # Tìm tất cả crossmaps giữa hai domain
    crossmaps = db.query(crud.disease_domain_crossmap.model).filter(
        ((crud.disease_domain_crossmap.model.domain_id_1 == domain_id1) & 
         (crud.disease_domain_crossmap.model.domain_id_2 == domain_id2)) | 
        ((crud.disease_domain_crossmap.model.domain_id_1 == domain_id2) & 
         (crud.disease_domain_crossmap.model.domain_id_2 == domain_id1))
    ).all()
    
    result = []
    for crossmap in crossmaps:
        # Xác định đâu là source và target dựa trên thứ tự domain_id
        if crossmap.domain_id_1 == domain_id1:
            source_disease_id = crossmap.disease_id_1
            target_disease_id = crossmap.disease_id_2
            source_domain_id = crossmap.domain_id_1
            target_domain_id = crossmap.domain_id_2
        else:
            source_disease_id = crossmap.disease_id_2
            target_disease_id = crossmap.disease_id_1
            source_domain_id = crossmap.domain_id_2
            target_domain_id = crossmap.domain_id_1
        
        # Lấy thông tin disease từ source và target
        source_disease = crud.disease.get(db, source_disease_id)
        target_disease = crud.disease.get(db, target_disease_id)
        
        if source_disease and target_disease:
            result.append({
                "crossmap_id": crossmap.id,
                "source_disease_id": source_disease_id,
                "target_disease_id": target_disease_id,
                "source_disease_label": source_disease.label,
                "target_disease_label": target_disease.label
            })
    
    return result

def normalize_disease_name(name: str) -> str:
    """
    Chuẩn hóa tên bệnh để cải thiện fuzzy matching
    
    Args:
        name: Tên bệnh gốc
        
    Returns:
        str: Tên bệnh đã được chuẩn hóa
    """
    if not name:
        return ""
    
    # Chuyển về chữ thường
    normalized = name.lower()
    
    # Loại bỏ nội dung trong ngoặc đơn và ngoặc vuông
    import re
    normalized = re.sub(r'\([^)]*\)', '', normalized)
    normalized = re.sub(r'\[[^\]]*\]', '', normalized)
    
    # Loại bỏ dấu câu và ký tự đặc biệt không cần thiết
    normalized = re.sub(r'[^\w\sáàảãạâấầẩẫậăắằẳẵặéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ]', ' ', normalized)
    
    # Loại bỏ khoảng trắng thừa
    normalized = ' '.join(normalized.split())
    
    return normalized.strip()

def find_best_disease_match(
    query_name: str,
    disease_labels: List[str],
    diseases: List,
    min_score: int = 60
) -> Optional[tuple]:
    """
    Tìm disease match tốt nhất với improved fuzzy matching
    
    Args:
        query_name: Tên bệnh cần tìm
        disease_labels: Danh sách label diseases
        diseases: Danh sách disease objects
        min_score: Điểm tối thiểu để accept match
        
    Returns:
        tuple: (matched_disease_object, matched_label, score) hoặc None
    """
    if not query_name or not disease_labels:
        return None
    
    # Normalize query
    normalized_query = normalize_disease_name(query_name)
    logger.app_info(f"Tìm match cho: '{query_name}' -> normalized: '{normalized_query}'")
    
    # Tạo mapping từ normalized labels tới original labels và diseases
    label_mapping = {}
    normalized_labels = []
    
    for i, label in enumerate(disease_labels):
        normalized_label = normalize_disease_name(label)
        normalized_labels.append(normalized_label)
        label_mapping[normalized_label] = {
            "original_label": label,
            "disease": diseases[i]
        }
    
    # Log một vài ví dụ normalized labels để debug
    logger.app_info(f"Một vài normalized labels: {normalized_labels[:5]}")
    
    # Thử multiple fuzzy matching strategies
    best_match = None
    best_score = 0
    
    # Strategy 1: fuzz.ratio với normalized text
    match1 = process.extractOne(
        normalized_query,
        normalized_labels,
        scorer=fuzz.ratio,
        score_cutoff=min_score
    )
    
    if match1 and match1[1] > best_score:
        best_match = match1
        best_score = match1[1]
        logger.app_info(f"fuzz.ratio match: '{match1[0]}' với score {match1[1]}")
    
    # Strategy 2: fuzz.partial_ratio với normalized text  
    match2 = process.extractOne(
        normalized_query,
        normalized_labels,
        scorer=fuzz.partial_ratio,
        score_cutoff=min_score
    )
    
    if match2 and match2[1] > best_score:
        best_match = match2
        best_score = match2[1]
        logger.app_info(f"fuzz.partial_ratio match: '{match2[0]}' với score {match2[1]}")
    
    # Strategy 3: fuzz.token_sort_ratio với normalized text
    match3 = process.extractOne(
        normalized_query,
        normalized_labels,
        scorer=fuzz.token_sort_ratio,
        score_cutoff=min_score
    )
    
    if match3 and match3[1] > best_score:
        best_match = match3
        best_score = match3[1]
        logger.app_info(f"fuzz.token_sort_ratio match: '{match3[0]}' với score {match3[1]}")
    
    # Strategy 4: Exact match với original text (case insensitive)
    for label in disease_labels:
        if query_name.lower() == label.lower():
            matched_normalized = normalize_disease_name(label)
            logger.app_info(f"Exact match tìm thấy: '{label}' cho query '{query_name}'")
            return (
                label_mapping[matched_normalized]["disease"],
                label_mapping[matched_normalized]["original_label"],
                100.0
            )
    
    if best_match:
        matched_info = label_mapping[best_match[0]]
        logger.app_info(f"Best match cuối cùng: '{matched_info['original_label']}' với score {best_match[1]}")
        return (
            matched_info["disease"],
            matched_info["original_label"],
            best_match[1]
        )
    
    logger.app_info(f"Không tìm thấy match nào cho '{query_name}' với min_score={min_score}")
    return None

async def import_crossmaps_from_json(
    target_domain_name: str,
    mappings: Dict[str, str],
    db: Session,
    created_by: Optional[str] = None
) -> Dict[str, Any]:
    """
    Import ánh xạ từ JSON format với fuzzy matching
    
    Args:
        target_domain_name: Tên domain đích
        mappings: Dict {"tên bệnh domain đích": "tên bệnh STANDARD"}
        db: Database session
        created_by: Người tạo ánh xạ
        
    Returns:
        Dict[str, Any]: Kết quả import
    """
    # Tìm domain đích theo tên (fuzzy matching)
    all_domains = db.query(crud.domain.model).filter(
        crud.domain.model.deleted_at.is_(None)
    ).all()
    
    domain_names = [domain.domain for domain in all_domains]
    target_domain_match = process.extractOne(
        target_domain_name, 
        domain_names, 
        scorer=fuzz.ratio,
        score_cutoff=80
    )
    
    if not target_domain_match:
        raise HTTPException(
            status_code=404, 
            detail=f"Không tìm thấy domain khớp với tên '{target_domain_name}'"
        )
    
    # Lấy domain đích
    target_domain = next(d for d in all_domains if d.domain == target_domain_match[0])
    
    # Tìm domain STANDARD
    standard_domain = db.query(crud.domain.model).filter(
        crud.domain.model.domain.ilike("STANDARD"),
        crud.domain.model.deleted_at.is_(None)
    ).first()
    
    if not standard_domain:
        raise HTTPException(status_code=404, detail="Không tìm thấy domain STANDARD")
    
    # Lấy tất cả diseases trong target domain và standard domain
    target_diseases = db.query(crud.disease.model).filter(
        crud.disease.model.domain_id == target_domain.id,
        crud.disease.model.deleted_at.is_(None)
    ).all()
    
    standard_diseases = db.query(crud.disease.model).filter(
        crud.disease.model.domain_id == standard_domain.id,
        crud.disease.model.deleted_at.is_(None)
    ).all()
    
    target_disease_labels = [disease.label for disease in target_diseases]
    standard_disease_labels = [disease.label for disease in standard_diseases]
    
    # Debug: Log danh sách diseases trong STANDARD domain
    logger.app_info(f"STANDARD domain có {len(standard_diseases)} diseases:")
    for label in standard_disease_labels[:10]:  # Log 10 diseases đầu tiên để debug
        logger.app_info(f"  - {label}")
    if len(standard_disease_labels) > 10:
        logger.app_info(f"  ... và {len(standard_disease_labels) - 10} diseases khác")
    
    # Xóa tất cả ánh xạ cũ giữa target domain và standard domain
    existing_crossmaps = db.query(crud.disease_domain_crossmap.model).filter(
        ((crud.disease_domain_crossmap.model.domain_id_1 == target_domain.id) & 
         (crud.disease_domain_crossmap.model.domain_id_2 == standard_domain.id)) | 
        ((crud.disease_domain_crossmap.model.domain_id_1 == standard_domain.id) & 
         (crud.disease_domain_crossmap.model.domain_id_2 == target_domain.id))
    ).all()
    
    for crossmap in existing_crossmaps:
        db.delete(crossmap)
    db.commit()
    
    # Xử lý từng mapping
    results = {
        "success": [],
        "failed": []
    }
    
    for target_disease_name, standard_disease_name in mappings.items():
        try:
            # Sử dụng improved fuzzy matching cho target disease
            target_match_result = find_best_disease_match(
                query_name=target_disease_name,
                disease_labels=target_disease_labels,
                diseases=target_diseases,
                min_score=60
            )
            
            if not target_match_result:
                results["failed"].append({
                    "target_disease_name": target_disease_name,
                    "standard_disease_name": standard_disease_name,
                    "error": f"Không tìm thấy bệnh khớp với '{target_disease_name}' trong domain đích"
                })
                continue
            
            target_disease, target_matched_label, target_score = target_match_result
            
            # Sử dụng improved fuzzy matching cho standard disease
            standard_match_result = find_best_disease_match(
                query_name=standard_disease_name,
                disease_labels=standard_disease_labels,
                diseases=standard_diseases,
                min_score=60
            )
            
            if not standard_match_result:
                results["failed"].append({
                    "target_disease_name": target_disease_name,
                    "standard_disease_name": standard_disease_name,
                    "error": f"Không tìm thấy bệnh khớp với '{standard_disease_name}' trong domain STANDARD"
                })
                continue
            
            standard_disease, standard_matched_label, standard_score = standard_match_result
            
            # Tạo crossmap mới
            crossmap_data = DiseaseDomainCrossmapCreate(
                disease_id_1=standard_disease.id,
                domain_id_1=standard_domain.id,
                disease_id_2=target_disease.id,
                domain_id_2=target_domain.id
            )
            
            new_crossmap = crud.disease_domain_crossmap.create(db, obj_in=crossmap_data)
            
            # Tạo ánh xạ trong ChromaDB
            try:
                chromadb_instance.create_mapping(
                    domain_id=target_domain.id,
                    domain_disease_id=target_disease.id,
                    label_id=standard_disease.id,
                    label=standard_disease.label
                )
            except Exception as e:
                logger.error(f"Lỗi khi tạo ánh xạ trong ChromaDB: {str(e)}")
            
            results["success"].append({
                "id": new_crossmap.id,
                "target_disease_name": target_disease_name,
                "target_disease_matched": target_matched_label,
                "target_disease_id": target_disease.id,
                "standard_disease_name": standard_disease_name,
                "standard_disease_matched": standard_matched_label,
                "standard_disease_id": standard_disease.id,
                "target_match_score": target_score,
                "standard_match_score": standard_score
            })
            
        except Exception as e:
            results["failed"].append({
                "target_disease_name": target_disease_name,
                "standard_disease_name": standard_disease_name,
                "error": str(e)
            })
    
    return {
        "target_domain_id": target_domain.id,
        "target_domain_name": target_domain.domain,
        "target_domain_matched": target_domain_match[0],
        "target_domain_match_score": target_domain_match[1],
        "standard_domain_id": standard_domain.id,
        "standard_domain_name": standard_domain.domain,
        "total_mappings": len(mappings),
        "success_count": len(results["success"]),
        "failed_count": len(results["failed"]),
        "results": results
    }

async def export_crossmaps_to_json(
    target_domain_id: str,
    db: Session
) -> Dict[str, Any]:
    """
    Export ánh xạ sang JSON format
    
    Args:
        target_domain_id: ID của domain đích
        db: Database session
        
    Returns:
        Dict[str, Any]: Dữ liệu export
    """
    # Kiểm tra target domain có tồn tại không
    target_domain = crud.domain.get(db, id=target_domain_id)
    if not target_domain or target_domain.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Domain đích không tồn tại hoặc đã bị xóa")
    
    # Tìm domain STANDARD
    standard_domain = db.query(crud.domain.model).filter(
        crud.domain.model.domain.ilike("STANDARD"),
        crud.domain.model.deleted_at.is_(None)
    ).first()
    
    if not standard_domain:
        raise HTTPException(status_code=404, detail="Không tìm thấy domain STANDARD")
    
    # Tìm tất cả crossmaps giữa target domain và standard domain
    crossmaps = db.query(crud.disease_domain_crossmap.model).filter(
        ((crud.disease_domain_crossmap.model.domain_id_1 == target_domain_id) & 
         (crud.disease_domain_crossmap.model.domain_id_2 == standard_domain.id)) | 
        ((crud.disease_domain_crossmap.model.domain_id_1 == standard_domain.id) & 
         (crud.disease_domain_crossmap.model.domain_id_2 == target_domain_id))
    ).all()
    
    # Tạo mapping dict
    mappings = {}
    
    for crossmap in crossmaps:
        # Xác định đâu là target disease và standard disease
        if crossmap.domain_id_1 == target_domain_id:
            target_disease_id = crossmap.disease_id_1
            standard_disease_id = crossmap.disease_id_2
        else:
            target_disease_id = crossmap.disease_id_2
            standard_disease_id = crossmap.disease_id_1
        
        # Lấy thông tin disease
        target_disease = crud.disease.get(db, target_disease_id)
        standard_disease = crud.disease.get(db, standard_disease_id)
        
        if target_disease and standard_disease:
            mappings[target_disease.label] = standard_disease.label
    
    return {
        "target_domain_id": target_domain_id,
        "target_domain_name": target_domain.domain,
        "standard_domain_id": standard_domain.id,
        "standard_domain_name": standard_domain.domain,
        "mappings": mappings,
        "total_mappings": len(mappings)
    } 