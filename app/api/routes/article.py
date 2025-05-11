from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from sqlalchemy.orm import Session

from app.db.sqlite_service import get_db
from app.services import article_service
from app.models.database import Article, ArticleCreate, ArticleUpdate
from app.api.routes.auth import get_current_user

router = APIRouter()

@router.get("/", response_model=List[Dict[str, Any]])
async def get_articles(
    skip: int = 0, 
    limit: int = 100,
    search: Optional[str] = None,
    author_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách các bài viết
    """
    articles = await article_service.get_all_articles(
        skip=skip,
        limit=limit,
        search=search,
        author_id=author_id,
        db=db
    )
    # Filter out soft-deleted articles
    return [article for article in articles if not article.get("deleted_at")]

@router.post("/", response_model=Dict[str, Any])
async def create_article(
    article: ArticleCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Tạo bài viết mới
    """
    return await article_service.create_article(
        article_data=article,
        creator_id=current_user["user_id"],
        db=db
    )

@router.get("/{article_id}", response_model=Dict[str, Any])
async def get_article(
    article_id: str = Path(..., description="ID của bài viết"),
    db: Session = Depends(get_db)
):
    """
    Lấy thông tin chi tiết của một bài viết
    """
    article_data = await article_service.get_article_by_id(article_id=article_id, db=db)
    if article_data.get("deleted_at"):
        raise HTTPException(status_code=404, detail="Không tìm thấy bài viết này hoặc đã bị xóa")
    return article_data

@router.put("/{article_id}", response_model=Dict[str, Any])
async def update_article(
    article_id: str = Path(..., description="ID của bài viết"),
    article: ArticleUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Cập nhật thông tin bài viết
    """
    return await article_service.update_article(
        article_id=article_id,
        article_data=article,
        updater_id=current_user["user_id"],
        db=db
    )

@router.delete("/{article_id}", response_model=Dict[str, Any])
async def delete_article(
    article_id: str = Path(..., description="ID của bài viết"),
    soft_delete: bool = True,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Xóa bài viết (mặc định là soft delete)
    """
    return await article_service.delete_article(
        article_id=article_id,
        soft_delete=soft_delete,
        deleted_by=current_user["user_id"],
        db=db
    )

@router.get("/search/{search_term}", response_model=List[Dict[str, Any]])
async def search_articles(
    search_term: str = Path(..., description="Từ khóa tìm kiếm"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Tìm kiếm bài viết theo tiêu đề hoặc nội dung
    """
    articles = await article_service.search_articles(
        search_term=search_term,
        skip=skip,
        limit=limit,
        db=db
    )
    # Filter out soft-deleted articles
    return [article for article in articles if not article.get("deleted_at")] 