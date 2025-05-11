#!/usr/bin/env python3
"""
Script khởi tạo cơ sở dữ liệu và thêm thông tin mặc định:
- Tạo role ADMIN 
- Tạo tài khoản admin với role ADMIN
"""
import os
import sys
import argparse
import hashlib
import uuid
from datetime import datetime, timezone
import sqlite3

# Thêm thư mục gốc vào sys.path để import các module từ app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import helper module để xử lý vấn đề timezone.UTC
from app.core.datetime_helper import timezone

from app.core.config import settings
from app.db.sqlite_service import init_db, get_db
from app.models.database import RoleCreate, UserInfoCreate
from app.db import crud

def create_admin_role(db) -> str:
    """
    Tạo role ADMIN nếu chưa tồn tại
    
    Returns:
        str: ID của role ADMIN
    """
    existing_role = crud.role.get_by_name(db, role_name="ADMIN")
    if existing_role:
        print(f"Role ADMIN đã tồn tại với ID: {existing_role.role_id}")
        return existing_role.role_id
    
    role_data = RoleCreate(role="ADMIN")
    role = crud.role.create(db, obj_in=role_data)
    print(f"Đã tạo role ADMIN với ID: {role.role_id}")
    return role.role_id

def create_admin_user(db, username, password, role_id) -> str:
    """
    Tạo tài khoản admin với role ADMIN
    
    Args:
        db: Database session
        username: Tên đăng nhập của admin
        password: Mật khẩu của admin
        role_id: ID của role ADMIN
        
    Returns:
        str: ID của user admin
    """
    # Kiểm tra xem user đã tồn tại chưa
    existing_user = crud.user.get_by_username(db, username=username)
    if existing_user:
        print(f"Tài khoản {username} đã tồn tại với ID: {existing_user.user_id}")
        return existing_user.user_id
    
    # Hash mật khẩu bằng SHA256
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    # Tạo user admin
    user_data = UserInfoCreate(
        username=username,
        hashpass=hashed_password,
        role_id=role_id
    )
    
    user = crud.user.create(db, obj_in=user_data)
    print(f"Đã tạo tài khoản admin {username} với ID: {user.user_id}")
    return user.user_id

def initialize_image_usages(db):
    """Khởi tạo các loại sử dụng hình ảnh"""
    from app.services.image_management_service import init_image_usages
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(init_image_usages(db))
        print("Đã khởi tạo các loại sử dụng hình ảnh")
    except Exception as e:
        print(f"Lỗi khi khởi tạo các loại sử dụng hình ảnh: {str(e)}")

def ensure_image_directories():
    """Đảm bảo các thư mục lưu trữ hình ảnh tồn tại"""
    from app.services.image_management_service import IMAGE_ROOT_DIR, VALID_OBJECT_TYPES
    
    for object_type in VALID_OBJECT_TYPES:
        dir_path = os.path.join(IMAGE_ROOT_DIR, object_type)
        os.makedirs(dir_path, exist_ok=True)
        print(f"Đã đảm bảo thư mục hình ảnh tồn tại: {dir_path}")

def main():
    parser = argparse.ArgumentParser(description="Khởi tạo cơ sở dữ liệu và tạo tài khoản admin")
    parser.add_argument("--username", type=str, required=True, help="Tên đăng nhập của admin")
    parser.add_argument("--password", type=str, required=True, help="Mật khẩu của admin")
    parser.add_argument("--force", action="store_true", help="Xóa database cũ nếu đã tồn tại")
    parser.add_argument("--db-path", type=str, help="Đường dẫn tới file database sqlite")
    
    args = parser.parse_args()
    
    # Sử dụng đường dẫn từ tham số hoặc từ settings
    db_path = args.db_path if args.db_path else settings.SQLITE_DB_PATH
    print(f"Sử dụng database tại: {db_path}")
    
    # Đảm bảo thư mục chứa database tồn tại
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Kiểm tra xem database có tồn tại không và tùy chọn xóa nếu được yêu cầu
    if os.path.exists(db_path) and args.force:
        print(f"Xóa database cũ: {db_path}")
        os.remove(db_path)
    
    # Khởi tạo cơ sở dữ liệu
    print("Khởi tạo cơ sở dữ liệu...")
    init_db()
    
    # Tạo thư mục lưu trữ hình ảnh
    ensure_image_directories()
    
    # Lấy một phiên làm việc với database
    db_generator = get_db()
    db = next(db_generator)
    
    try:
        # Tạo role ADMIN
        role_id = create_admin_role(db)
        
        # Tạo tài khoản admin
        user_id = create_admin_user(db, args.username, args.password, role_id)
        
        # Khởi tạo các loại sử dụng hình ảnh
        initialize_image_usages(db)
        
        print("Khởi tạo cơ sở dữ liệu thành công!")
    except Exception as e:
        print(f"Lỗi khi khởi tạo cơ sở dữ liệu: {str(e)}")
    finally:
        # Đóng phiên làm việc
        db_generator.close()

if __name__ == "__main__":
    main() 