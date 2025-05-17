"""
Service xử lý logic cho bài viết
"""
from typing import List, Dict, Any, Optional, Tuple
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.db import crud
from app.models.database import ArticleCreate, ArticleUpdate
from app.services.utils import filter_user_data

async def get_all_articles(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    author_id: Optional[str] = None,
    include_deleted: bool = False,
    db: Session = None
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Lấy danh sách các bài viết
    
    Returns:
        Tuple[List[Dict[str, Any]], int]: Danh sách bài viết và tổng số records
    """
    if search:
        articles = crud.article.search_articles(db, search, skip=skip, limit=limit)
        total = count_articles_by_search(search, db)
    elif author_id:
        articles = crud.article.get_by_author(db, author_id, skip=skip, limit=limit)
        total = count_articles_by_author(author_id, db)
    else:
        query = db.query(crud.article.model)
        if not include_deleted:
            query = query.filter(crud.article.model.deleted_at.is_(None))
        articles = query.offset(skip).limit(limit).all()
        total = count_all_articles(include_deleted, db)
    
    # Lấy thông tin người tạo cho mỗi bài viết
    result = []
    for article in articles:
        # Loại bỏ _sa_instance_state
        article_dict = {k: v for k, v in article.__dict__.items() if k != "_sa_instance_state"}
        if article.created_by:
            creator = crud.user.get(db, article.created_by)
            if creator:
                # Lọc thông tin nhạy cảm từ creator
                creator_dict = filter_user_data({k: v for k, v in creator.__dict__.items() if k != "_sa_instance_state"})
                article_dict["creator"] = creator_dict
        
        # Lấy các hình ảnh liên quan
        try:
            from app.services import image_management_service
            images = await image_management_service.get_images_for_object("article", article.id, db)
            article_dict["images"] = images
        except Exception as e:
            article_dict["images"] = []
        
        result.append(article_dict)
    
    return result, total

# Helper functions để đếm tổng số records

def count_articles_by_search(search_term: str, db: Session) -> int:
    """Helper function để đếm số bài viết theo kết quả tìm kiếm"""
    search_pattern = f"%{search_term}%"
    return db.query(func.count(crud.article.model.id)).filter(
        or_(
            crud.article.model.title.ilike(search_pattern),
            crud.article.model.content.ilike(search_pattern)
        ),
        crud.article.model.deleted_at.is_(None)
    ).scalar()

def count_articles_by_author(author_id: str, db: Session) -> int:
    """Helper function để đếm số bài viết theo tác giả"""
    return db.query(func.count(crud.article.model.id)).filter(
        crud.article.model.created_by == author_id,
        crud.article.model.deleted_at.is_(None)
    ).scalar()

def count_all_articles(include_deleted: bool, db: Session) -> int:
    """Helper function để đếm tất cả bài viết"""
    query = db.query(func.count(crud.article.model.id))
    
    if not include_deleted:
        query = query.filter(crud.article.model.deleted_at.is_(None))
        
    return query.scalar()

async def get_article_by_id(article_id: str, db: Session) -> Dict[str, Any]:
    """Lấy thông tin chi tiết của một bài viết"""
    article = crud.article.get(db, id=article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài viết")
    
    # Loại bỏ _sa_instance_state
    result = {k: v for k, v in article.__dict__.items() if k != "_sa_instance_state"}
    
    # Thêm thông tin người tạo
    if article.created_by:
        creator = crud.user.get(db, article.created_by)
        if creator:
            # Lọc thông tin nhạy cảm từ creator
            creator_dict = filter_user_data({k: v for k, v in creator.__dict__.items() if k != "_sa_instance_state"})
            result["creator"] = creator_dict
    
    # Lấy các hình ảnh liên quan
    try:
        from app.services import image_management_service
        images = await image_management_service.get_images_for_object("article", article_id, db)
        result["images"] = images
    except Exception as e:
        result["images"] = []
    
    return result

async def create_article(article_data: ArticleCreate, creator_id: Optional[str], db: Session) -> Dict[str, Any]:
    """Tạo một bài viết mới"""
    # Kiểm tra xem người tạo có tồn tại không
    if creator_id:
        creator = crud.user.get(db, id=creator_id)
        if not creator:
            raise HTTPException(status_code=404, detail="Người dùng không tồn tại")
        article_dict = article_data.model_dump()
        article_dict["created_by"] = creator_id
        article_data = ArticleCreate(**article_dict)
    
    article = crud.article.create(db, obj_in=article_data)
    
    # Trả về một dict sạch không chứa _sa_instance_state
    result = {k: v for k, v in article.__dict__.items() if k != "_sa_instance_state"}
    return result

async def update_article(article_id: str, article_data: ArticleUpdate, updater_id: Optional[str], db: Session) -> Dict[str, Any]:
    """Cập nhật thông tin bài viết"""
    article = crud.article.get(db, id=article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài viết")
    
    # Thêm thông tin người cập nhật
    if updater_id:
        updater = crud.user.get(db, id=updater_id)
        if not updater:
            raise HTTPException(status_code=404, detail="Người dùng không tồn tại")
        article_dict = article_data.model_dump(exclude_unset=True)
        article_dict["updated_by"] = updater_id
        article_data = ArticleUpdate(**article_dict)
    
    updated_article = crud.article.update(db, db_obj=article, obj_in=article_data)
    
    # Trả về một dict sạch không chứa _sa_instance_state
    result = {k: v for k, v in updated_article.__dict__.items() if k != "_sa_instance_state"}
    return result

async def delete_article(article_id: str, soft_delete: bool = True, deleted_by: Optional[str] = None, db: Session = None) -> Dict[str, Any]:
    """Xóa một bài viết"""
    article = crud.article.get(db, id=article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài viết")
    
    # Kiểm tra người xóa
    if deleted_by:
        deleter = crud.user.get(db, id=deleted_by)
        if not deleter:
            raise HTTPException(status_code=404, detail="Người dùng không tồn tại")
    
    if soft_delete:
        deleted_article = crud.article.soft_delete(db, id=article_id, deleted_by=deleted_by)
    else:
        deleted_article = crud.article.remove(db, id=article_id)
    
    return {"success": True, "article_id": article_id}

async def search_articles(search_term: str, skip: int = 0, limit: int = 100, db: Session = None) -> Tuple[List[Dict[str, Any]], int]:
    """
    Tìm kiếm bài viết theo tiêu đề hoặc nội dung
    
    Returns:
        Tuple[List[Dict[str, Any]], int]: Danh sách bài viết và tổng số records
    """
    articles = crud.article.search_articles(db, search_term, skip=skip, limit=limit)
    total = count_articles_by_search(search_term, db)
    
    # Trả về danh sách đã bao gồm thông tin hình ảnh
    result = []
    for article in articles:
        # Loại bỏ _sa_instance_state
        article_dict = {k: v for k, v in article.__dict__.items() if k != "_sa_instance_state"}
        
        # Lấy các hình ảnh liên quan
        try:
            from app.services import image_management_service
            images = await image_management_service.get_images_for_object("article", article.id, db)
            article_dict["images"] = images
        except Exception as e:
            article_dict["images"] = []
        
        result.append(article_dict)
    
    return result, total 