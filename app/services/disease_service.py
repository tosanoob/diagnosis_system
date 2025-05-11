"""
Service xử lý logic cho bệnh
"""
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db import crud
from app.models.database import DiseaseCreate, DiseaseUpdate

async def get_all_diseases(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
    domain_id: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = None
) -> List[Dict[str, Any]]:
    """Lấy danh sách các bệnh"""
    if search:
        diseases = crud.disease.search_diseases(db, search, skip=skip, limit=limit)
    elif domain_id:
        diseases = crud.disease.get_by_domain_id(db, domain_id, skip=skip, limit=limit)
    elif active_only:
        diseases = crud.disease.get_active_diseases(db, skip=skip, limit=limit)
    else:
        diseases = crud.disease.get_all(db, skip=skip, limit=limit)
    
    # Lấy thông tin domain cho mỗi bệnh
    result = []
    for disease in diseases:
        # Loại bỏ _sa_instance_state
        disease_dict = {k: v for k, v in disease.__dict__.items() if k != "_sa_instance_state"}
        if disease.domain_id:
            domain = crud.domain.get(db, disease.domain_id)
            if domain:
                # Chuyển domain thành dict sạch
                domain_dict = {k: v for k, v in domain.__dict__.items() if k != "_sa_instance_state"}
                disease_dict["domain"] = domain_dict
        result.append(disease_dict)
    
    return result

async def get_disease_by_id(disease_id: str, db: Session) -> Dict[str, Any]:
    """Lấy thông tin chi tiết của một bệnh"""
    disease = crud.disease.get(db, id=disease_id)
    if not disease:
        raise HTTPException(status_code=404, detail="Không tìm thấy bệnh")
    
    # Loại bỏ _sa_instance_state
    result = {k: v for k, v in disease.__dict__.items() if k != "_sa_instance_state"}
    
    # Thêm thông tin domain
    if disease.domain_id:
        domain = crud.domain.get(db, disease.domain_id)
        if domain:
            # Chuyển domain thành dict sạch
            domain_dict = {k: v for k, v in domain.__dict__.items() if k != "_sa_instance_state"}
            result["domain"] = domain_dict
    
    # Thêm thông tin bài viết
    if disease.article_id:
        article = crud.article.get(db, disease.article_id)
        if article:
            # Chuyển article thành dict sạch
            article_dict = {k: v for k, v in article.__dict__.items() if k != "_sa_instance_state"}
            result["article"] = article_dict
    
    # Lấy các hình ảnh liên quan
    try:
        from app.services import image_management_service
        images = await image_management_service.get_images_for_object("disease", disease_id, db)
        result["images"] = images
    except Exception as e:
        result["images"] = []
    
    return result

async def create_disease(disease_data: DiseaseCreate, db: Session, created_by: Optional[str] = None) -> Dict[str, Any]:
    """Tạo một bệnh mới"""
    # Kiểm tra xem domain có tồn tại không
    if disease_data.domain_id:
        domain = crud.domain.get(db, id=disease_data.domain_id)
        if not domain:
            raise HTTPException(status_code=404, detail="Domain không tồn tại")
    
    # Kiểm tra xem bài viết có tồn tại không
    if disease_data.article_id:
        article = crud.article.get(db, id=disease_data.article_id)
        if not article:
            raise HTTPException(status_code=404, detail="Bài viết không tồn tại")
    
    # Thêm thông tin người tạo
    if created_by:
        disease_dict = disease_data.model_dump()
        disease_dict["created_by"] = created_by
        disease_data = DiseaseCreate(**disease_dict)
    
    disease = crud.disease.create(db, obj_in=disease_data)
    
    # Trả về một dict sạch không chứa _sa_instance_state
    result = {k: v for k, v in disease.__dict__.items() if k != "_sa_instance_state"}
    return result

async def update_disease(disease_id: str, disease_data: DiseaseUpdate, db: Session, updated_by: Optional[str] = None) -> Dict[str, Any]:
    """Cập nhật thông tin bệnh"""
    disease = crud.disease.get(db, id=disease_id)
    if not disease:
        raise HTTPException(status_code=404, detail="Không tìm thấy bệnh")
    
    # Kiểm tra xem domain có tồn tại không
    if disease_data.domain_id:
        domain = crud.domain.get(db, id=disease_data.domain_id)
        if not domain:
            raise HTTPException(status_code=404, detail="Domain không tồn tại")
    
    # Kiểm tra xem bài viết có tồn tại không
    if disease_data.article_id:
        article = crud.article.get(db, id=disease_data.article_id)
        if not article:
            raise HTTPException(status_code=404, detail="Bài viết không tồn tại")
    
    # Thêm thông tin người cập nhật
    if updated_by:
        disease_dict = disease_data.model_dump(exclude_unset=True)
        disease_dict["updated_by"] = updated_by
        disease_data = DiseaseUpdate(**disease_dict)
    
    updated_disease = crud.disease.update(db, db_obj=disease, obj_in=disease_data)
    
    # Trả về một dict sạch không chứa _sa_instance_state
    result = {k: v for k, v in updated_disease.__dict__.items() if k != "_sa_instance_state"}
    return result

async def delete_disease(disease_id: str, soft_delete: bool = True, deleted_by: Optional[str] = None, db: Session = None) -> Dict[str, Any]:
    """Xóa một bệnh"""
    disease = crud.disease.get(db, id=disease_id)
    if not disease:
        raise HTTPException(status_code=404, detail="Không tìm thấy bệnh")
    
    if soft_delete:
        deleted_disease = crud.disease.soft_delete(db, id=disease_id, deleted_by=deleted_by)
    else:
        deleted_disease = crud.disease.remove(db, id=disease_id)
    
    return {"success": True, "disease_id": disease_id}

async def get_disease_by_domain(domain_id: str, skip: int = 0, limit: int = 100, db: Session = None) -> List[Dict[str, Any]]:
    """Lấy danh sách các bệnh theo domain"""
    diseases = crud.disease.get_by_domain_id(db, domain_id, skip=skip, limit=limit)
    # Trả về danh sách các dict sạch không chứa _sa_instance_state
    return [{k: v for k, v in disease.__dict__.items() if k != "_sa_instance_state"} for disease in diseases]

async def search_diseases(search_term: str, skip: int = 0, limit: int = 100, db: Session = None) -> List[Dict[str, Any]]:
    """Tìm kiếm bệnh theo tên hoặc mô tả"""
    diseases = crud.disease.search_diseases(db, search_term, skip=skip, limit=limit)
    # Trả về danh sách các dict sạch không chứa _sa_instance_state
    return [{k: v for k, v in disease.__dict__.items() if k != "_sa_instance_state"} for disease in diseases] 