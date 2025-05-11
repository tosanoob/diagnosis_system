"""
Service xử lý xác thực người dùng
"""
import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session

from app.core.datetime_helper import now_utc
from app.db import crud
from app.models.database import UserInfoCreate, UserInfoUpdate, UserTokenCreate
from app.db.sqlite_service import get_db

# Số giờ token có hiệu lực
TOKEN_EXPIRATION_HOURS = 24

def hash_password(password: str) -> str:
    """Mã hóa mật khẩu"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Xác minh mật khẩu"""
    return hash_password(plain_password) == hashed_password

async def register_user(username: str, password: str, role_id: Optional[str], db: Session) -> Dict[str, Any]:
    """Đăng ký người dùng mới"""
    # Kiểm tra xem tên đăng nhập đã tồn tại chưa
    existing_user = crud.user.get_by_username(db, username=username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Tên đăng nhập đã tồn tại")
    
    # Kiểm tra vai trò nếu được chỉ định
    if role_id:
        role = crud.role.get(db, id=role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Vai trò không tồn tại")
    
    # Mã hóa mật khẩu
    hashed_password = hash_password(password)
    
    # Tạo đối tượng người dùng mới
    user_data = UserInfoCreate(
        username=username,
        hashpass=hashed_password,
        role_id=role_id
    )
    
    # Lưu vào database
    user = crud.user.create(db, obj_in=user_data)
    
    return {
        "user_id": user.user_id,
        "username": user.username,
        "role_id": user.role_id,
        "created_at": user.created_at
    }

async def login_user(username: str, password: str, db: Session) -> Dict[str, Any]:
    """Đăng nhập và tạo token"""
    # Tìm người dùng theo tên đăng nhập
    user = crud.user.get_by_username(db, username=username)
    if not user:
        raise HTTPException(status_code=401, detail="Tên đăng nhập hoặc mật khẩu không chính xác")
    
    # Kiểm tra mật khẩu
    if not verify_password(password, user.hashpass):
        raise HTTPException(status_code=401, detail="Tên đăng nhập hoặc mật khẩu không chính xác")
    
    # Kiểm tra xem tài khoản có bị xóa không
    if user.deleted_at:
        raise HTTPException(status_code=401, detail="Tài khoản đã bị vô hiệu hóa")
    
    # Tạo token mới
    token = secrets.token_hex(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    # Tính thời gian hết hạn
    expiration = now_utc() + timedelta(hours=TOKEN_EXPIRATION_HOURS)
    
    # Lưu token vào database
    token_data = UserTokenCreate(
        user_id=user.user_id,
        token_hash=token_hash,
        expired_at=expiration,
        revoked=False
    )
    
    user_token = crud.user_token.create(db, obj_in=token_data)
    
    # Lấy thông tin vai trò
    role = None
    if user.role_id:
        role = crud.role.get(db, id=user.role_id)
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expiration,
        "user_id": user.user_id,
        "username": user.username,
        "role": role.role if role else None
    }

async def logout_user(token: str, db: Session) -> Dict[str, Any]:
    """Đăng xuất (thu hồi token)"""
    # Tính token hash
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    # Tìm token trong database
    user_token = crud.user_token.get_by_token_hash(db, token_hash=token_hash)
    if not user_token:
        raise HTTPException(status_code=404, detail="Token không tồn tại")
    
    # Thu hồi token
    revoked_token = crud.user_token.revoke_token(db, token_id=user_token.id)
    
    return {"success": True, "message": "Đăng xuất thành công"}

async def verify_token(token: str, db: Session) -> Dict[str, Any]:
    """Xác minh token và lấy thông tin người dùng"""
    # Tính token hash
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    # Tìm token trong database
    user_token = crud.user_token.get_by_token_hash(db, token_hash=token_hash)
    if not user_token:
        raise HTTPException(status_code=401, detail="Token không hợp lệ")
    
    # Kiểm tra xem token có hiệu lực không
    if user_token.revoked:
        raise HTTPException(status_code=401, detail="Token đã bị thu hồi")
    
    now = now_utc()
    # Đảm bảo cả hai datetime đều có timezone (offset-aware)
    expired_at = user_token.expired_at
    if expired_at.tzinfo is None:
        # Chuyển đổi naive datetime sang aware datetime với múi giờ UTC
        expired_at = expired_at.replace(tzinfo=timezone.utc)
    
    if expired_at < now:
        raise HTTPException(status_code=401, detail="Token đã hết hạn")
    
    # Lấy thông tin người dùng
    user = crud.user.get(db, id=user_token.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Người dùng không tồn tại")
    
    # Kiểm tra xem tài khoản có bị xóa không
    if user.deleted_at:
        raise HTTPException(status_code=401, detail="Tài khoản đã bị vô hiệu hóa")
    
    # Lấy thông tin vai trò
    role = None
    if user.role_id:
        role = crud.role.get(db, id=user.role_id)
    
    return {
        "user_id": user.user_id,
        "username": user.username,
        "role": role.role if role else None,
        "role_id": user.role_id
    }

async def change_password(user_id: str, old_password: str, new_password: str, db: Session) -> Dict[str, Any]:
    """Đổi mật khẩu"""
    # Tìm người dùng
    user = crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Người dùng không tồn tại")
    
    # Kiểm tra mật khẩu cũ
    if not verify_password(old_password, user.hashpass):
        raise HTTPException(status_code=401, detail="Mật khẩu hiện tại không chính xác")
    
    # Mã hóa mật khẩu mới
    hashed_password = hash_password(new_password)
    
    # Cập nhật mật khẩu
    user_data = UserInfoUpdate(hashpass=hashed_password)
    updated_user = crud.user.update(db, db_obj=user, obj_in=user_data)
    
    # Thu hồi tất cả token hiện tại
    revoked_count = crud.user_token.revoke_all_for_user(db, user_id=user_id)
    
    return {"success": True, "message": "Đổi mật khẩu thành công", "tokens_revoked": revoked_count} 