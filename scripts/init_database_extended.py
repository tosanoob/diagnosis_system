#!/usr/bin/env python3
"""
Script khởi tạo cơ sở dữ liệu mở rộng:
- Tạo domain STANDARD, mô tả 'Bệnh chuẩn theo Bộ y tế'
- Tạo 65 diseases từ standard_diseases trong file labels.json với domain STANDARD
- Tạo 3 bài đăng từ 3 bệnh Á VẢY NẾN, BẠCH BIẾN VÀ APTHOSE
- Tạo 3 phòng khám với hình ảnh
"""
import os
import sys
import json
import hashlib
import uuid
import asyncio
from datetime import datetime
import glob
from typing import Dict, List, Optional, Any

# Thêm thư mục gốc vào sys.path để import các module từ app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.datetime_helper import now_utc
from app.core.config import settings
from app.db.sqlite_service import init_db, get_db
from app.models.database import (
    RoleCreate, UserInfoCreate, DomainCreate, DiseaseCreate,
    ArticleCreate, ClinicCreate, ImageCreate, ImageMapCreate
)
from app.db import crud
from app.services import image_management_service

# Đường dẫn đến file labels.json
LABELS_JSON_PATH = "labels.json"
# Đường dẫn đến thư mục chunked_data
CHUNKED_DATA_DIR = "chunked_data"
# Đường dẫn đến thư mục hình ảnh
IMAGE_ROOT_DIR = "runtime/image"

def load_labels_data() -> Dict[str, Any]:
    """
    Đọc dữ liệu từ file labels.json
    
    Returns:
        Dict: Dữ liệu từ file labels.json
    """
    with open(LABELS_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def get_disease_description(disease_name: str) -> str:
    """
    Lấy mô tả bệnh từ các file chunked data
    
    Args:
        disease_name: Tên bệnh
        
    Returns:
        str: Mô tả bệnh, hoặc chuỗi rỗng nếu không tìm thấy
    """
    # Chuẩn hóa tên thư mục
    folder_name = disease_name.replace(" ", "_").replace("(", "").replace(")", "").replace("-", "_")
    folder_path = os.path.join(CHUNKED_DATA_DIR, folder_name)
    
    # Nếu không tìm thấy thư mục chính xác, thử tìm thư mục tương tự
    if not os.path.exists(folder_path):
        for dirname in os.listdir(CHUNKED_DATA_DIR):
            if dirname.startswith(disease_name.split()[0].replace("(", "").replace(")", "")):
                folder_path = os.path.join(CHUNKED_DATA_DIR, dirname)
                break
    
    # Nếu vẫn không tìm thấy, trả về chuỗi rỗng
    if not os.path.exists(folder_path):
        print(f"Không tìm thấy thư mục cho bệnh: {disease_name}")
        return ""
    
    # Tìm file _0.json (tổng quan)
    json_files = glob.glob(os.path.join(folder_path, "*.json"))
    content = ""
    
    # Đọc nội dung từ tất cả các file chunk
    for json_file in sorted(json_files):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                chunk_data = json.load(f)
                content += chunk_data.get("content", "") + "\n\n"
        except Exception as e:
            print(f"Lỗi khi đọc file {json_file}: {str(e)}")
    
    return content

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

def create_standard_domain(db, created_by: str) -> str:
    """
    Tạo domain STANDARD
    
    Args:
        db: Database session
        created_by: ID của người tạo
        
    Returns:
        str: ID của domain STANDARD
    """
    # Kiểm tra xem domain đã tồn tại chưa
    existing_domain = crud.domain.get_by_name(db, domain_name="STANDARD")
    if existing_domain:
        print(f"Domain STANDARD đã tồn tại với ID: {existing_domain.id}")
        return existing_domain.id
    
    # Tạo domain STANDARD
    domain_data = DomainCreate(
        domain="STANDARD",
        description="Bệnh chuẩn theo Bộ y tế",
        created_by=created_by
    )
    
    domain = crud.domain.create(db, obj_in=domain_data)
    print(f"Đã tạo domain STANDARD với ID: {domain.id}")
    return domain.id

def create_diseases(db, standard_diseases: List[str], domain_id: str, created_by: str):
    """
    Tạo danh sách bệnh từ standard_diseases
    
    Args:
        db: Database session
        standard_diseases: Danh sách tên bệnh chuẩn
        domain_id: ID của domain STANDARD
        created_by: ID của người tạo
    """
    created_count = 0
    for disease_name in standard_diseases:
        # Kiểm tra xem bệnh đã tồn tại chưa
        existing_disease = crud.disease.get_by_label(db, label=disease_name)
        if existing_disease:
            print(f"Bệnh {disease_name} đã tồn tại với ID: {existing_disease.id}")
            continue
        
        # Lấy mô tả bệnh từ chunked_data
        description = get_disease_description(disease_name)
        
        # Tạo bệnh mới
        disease_data = DiseaseCreate(
            label=disease_name,
            domain_id=domain_id,
            description=description,
            included_in_diagnosis=True
        )
        
        try:
            disease = crud.disease.create(db, obj_in=disease_data)
            
            # Cập nhật trường created_by
            disease.created_by = created_by
            db.add(disease)
            db.commit()
            
            created_count += 1
            print(f"Đã tạo bệnh {disease_name} với ID: {disease.id}")
        except Exception as e:
            print(f"Lỗi khi tạo bệnh {disease_name}: {str(e)}")
    
    print(f"Đã tạo {created_count} bệnh từ standard_diseases")

async def create_articles_with_images(db, created_by: str):
    """
    Tạo 3 bài đăng với hình ảnh cho 3 bệnh Á VẢY NẾN, BẠCH BIẾN VÀ APTHOSE
    
    Args:
        db: Database session
        created_by: ID của người tạo
    """
    # Danh sách bệnh cần tạo bài đăng
    diseases_for_articles = [
        "Á VẢY NẾN VÀ VẢY PHẤN DẠNG LICHEN (Parapsoriasis and Pityriasis Lichenoides)",
        "BỆNH BẠCH BIẾN (Vitiligo)",
        "BỆNH APTHOSE (Apthosis)"
    ]
    
    # Tên file hình ảnh tương ứng
    image_filenames = {
        "Á VẢY NẾN VÀ VẢY PHẤN DẠNG LICHEN (Parapsoriasis and Pityriasis Lichenoides)": "Á_VẢY_NẾN.png",
        "BỆNH BẠCH BIẾN (Vitiligo)": "BẠCH_BIẾN.webp",
        "BỆNH APTHOSE (Apthosis)": "BỆNH_APTHOSE.jpg"
    }
    
    for disease_name in diseases_for_articles:
        # Tìm bệnh trong database
        disease = crud.disease.get_by_label(db, label=disease_name)
        if not disease:
            print(f"Không tìm thấy bệnh {disease_name} trong database")
            continue
        
        # Lấy mô tả từ chunked_data làm nội dung bài viết
        content = get_disease_description(disease_name)
        
        # Tạo bài viết mới
        article_data = ArticleCreate(
            title=f"Thông tin về {disease_name}",
            summary=f"Thông tin chi tiết và hướng dẫn điều trị {disease_name}",
            content=content
        )
        
        try:
            article = crud.article.create(db, obj_in=article_data)
            
            # Cập nhật trường created_by
            article.created_by = created_by
            db.add(article)
            db.commit()
            
            # Cập nhật article_id trong disease
            disease.article_id = article.id
            db.add(disease)
            db.commit()
            
            print(f"Đã tạo bài viết cho bệnh {disease_name} với ID: {article.id}")
            
            # Thêm hình ảnh cho bài viết
            image_filename = image_filenames.get(disease_name)
            if image_filename:
                image_path = os.path.join(IMAGE_ROOT_DIR, "article", image_filename)
                if os.path.exists(image_path):
                    # Tạo bản ghi hình ảnh
                    image_data = ImageCreate(
                        base_url="/static/images",
                        rel_path=f"article/{image_filename}",
                        mime_type="image/jpeg" if image_filename.endswith(".jpg") else 
                                 "image/png" if image_filename.endswith(".png") else
                                 "image/webp" if image_filename.endswith(".webp") else "image/jpeg",
                        uploaded_by=created_by
                    )
                    
                    image = crud.image.create(db, obj_in=image_data)
                    
                    # Tạo bản ghi ImageMap
                    image_map_data = ImageMapCreate(
                        image_id=image.id,
                        object_type="article",
                        object_id=article.id,
                        usage="cover"
                    )
                    
                    image_map = crud.image_map.create(db, obj_in=image_map_data)
                    print(f"Đã thêm hình ảnh {image_filename} cho bài viết {article.id}")
                else:
                    print(f"Không tìm thấy file hình ảnh {image_path}")
        except Exception as e:
            print(f"Lỗi khi tạo bài viết cho bệnh {disease_name}: {str(e)}")

async def create_clinics_with_images(db, created_by: str):
    """
    Tạo 3 phòng khám với hình ảnh
    
    Args:
        db: Database session
        created_by: ID của người tạo
    """
    # Danh sách thông tin phòng khám
    clinics_info = [
        {
            "name": "Phòng khám Da liễu Trung ương",
            "description": "Phòng khám chuyên khoa da liễu hàng đầu với đội ngũ bác sĩ giàu kinh nghiệm",
            "location": "15 Phương Mai, Đống Đa, Hà Nội",
            "phone_number": "024 3576 3532",
            "website": "https://pkdalieutrunguong.vn",
            "image": "clinic1.jpg"
        },
        {
            "name": "Phòng khám Da liễu Sài Gòn",
            "description": "Phòng khám chuyên điều trị các bệnh da liễu với trang thiết bị hiện đại",
            "location": "123 Võ Văn Tần, Quận 3, TP. Hồ Chí Minh",
            "phone_number": "028 3930 9011",
            "website": "https://dalieusg.vn",
            "image": "clinic2.jpg"
        },
        {
            "name": "Trung tâm Da liễu Đông Á",
            "description": "Trung tâm điều trị da liễu theo tiêu chuẩn quốc tế",
            "location": "456 Nguyễn Khang, Cầu Giấy, Hà Nội",
            "phone_number": "024 7106 6858",
            "website": "https://dalieudonga.com",
            "image": "clinic3.jpg"
        }
    ]
    
    for clinic_info in clinics_info:
        # Tạo phòng khám mới
        clinic_data = ClinicCreate(
            name=clinic_info["name"],
            description=clinic_info["description"],
            location=clinic_info["location"],
            phone_number=clinic_info["phone_number"],
            website=clinic_info["website"]
        )
        
        try:
            clinic = crud.clinic.create(db, obj_in=clinic_data)
            
            # Cập nhật trường created_by
            clinic.created_by = created_by
            db.add(clinic)
            db.commit()
            
            print(f"Đã tạo phòng khám {clinic_info['name']} với ID: {clinic.id}")
            
            # Thêm hình ảnh cho phòng khám
            image_path = os.path.join(IMAGE_ROOT_DIR, "clinic", clinic_info["image"])
            if os.path.exists(image_path):
                # Tạo bản ghi hình ảnh
                image_data = ImageCreate(
                    base_url="/static/images",
                    rel_path=f"clinic/{clinic_info['image']}",
                    mime_type="image/jpeg",
                    uploaded_by=created_by
                )
                
                image = crud.image.create(db, obj_in=image_data)
                
                # Tạo bản ghi ImageMap
                image_map_data = ImageMapCreate(
                    image_id=image.id,
                    object_type="clinic",
                    object_id=clinic.id,
                    usage="cover"
                )
                
                image_map = crud.image_map.create(db, obj_in=image_map_data)
                print(f"Đã thêm hình ảnh {clinic_info['image']} cho phòng khám {clinic.id}")
            else:
                print(f"Không tìm thấy file hình ảnh {image_path}")
        except Exception as e:
            print(f"Lỗi khi tạo phòng khám {clinic_info['name']}: {str(e)}")

def initialize_image_usages(db):
    """Khởi tạo các loại sử dụng hình ảnh"""
    from app.services.image_management_service import init_image_usages
    
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
    import argparse
    
    parser = argparse.ArgumentParser(description="Khởi tạo cơ sở dữ liệu mở rộng")
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
        
        # Tạo domain STANDARD
        domain_id = create_standard_domain(db, user_id)
        
        # Tải dữ liệu từ labels.json
        labels_data = load_labels_data()
        standard_diseases = labels_data.get("standard_diseases", [])
        
        # Tạo diseases từ standard_diseases
        create_diseases(db, standard_diseases, domain_id, user_id)
        
        # Tạo bài đăng với hình ảnh
        loop = asyncio.get_event_loop()
        loop.run_until_complete(create_articles_with_images(db, user_id))
        
        # Tạo phòng khám với hình ảnh
        loop.run_until_complete(create_clinics_with_images(db, user_id))
        
        print("Khởi tạo cơ sở dữ liệu mở rộng thành công!")
    except Exception as e:
        print(f"Lỗi khi khởi tạo cơ sở dữ liệu: {str(e)}")
    finally:
        # Đóng phiên làm việc
        db_generator.close()

if __name__ == "__main__":
    main() 