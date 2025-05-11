# Scripts

Thư mục này chứa các script tiện ích cho hệ thống.

## Danh sách scripts

### 1. init_database.py

Script này dùng để khởi tạo cơ sở dữ liệu với các thông tin mặc định:
- Tạo role ADMIN
- Tạo tài khoản admin với quyền ADMIN
- Khởi tạo thư mục lưu trữ hình ảnh
- Khởi tạo các loại sử dụng hình ảnh (thumbnail, cover)

#### Cách sử dụng

```bash
# Cú pháp cơ bản
python scripts/init_database.py --username USERNAME --password PASSWORD

# Hoặc sử dụng trực tiếp
./scripts/init_database.py --username USERNAME --password PASSWORD

# Để xóa database cũ và tạo mới hoàn toàn
python scripts/init_database.py --username USERNAME --password PASSWORD --force

# Để chỉ định đường dẫn database khác
python scripts/init_database.py --username USERNAME --password PASSWORD --db-path /đường/dẫn/tới/database.sqlite3
```

#### Các tham số

- `--username`: Tên đăng nhập của tài khoản admin (bắt buộc)
- `--password`: Mật khẩu của tài khoản admin (bắt buộc) 
- `--force`: Xóa database cũ nếu đã tồn tại (tùy chọn)
- `--db-path`: Đường dẫn tới file database SQLite (tùy chọn, mặc định là `runtime/db.sqlite3`)

#### Ví dụ

```bash
# Tạo tài khoản admin với username "admin" và password "admin123"
python scripts/init_database.py --username admin --password admin123

# Xóa database cũ và tạo mới hoàn toàn
python scripts/init_database.py --username admin --password admin123 --force

# Sử dụng database ở đường dẫn tùy chỉnh
python scripts/init_database.py --username admin --password admin123 --db-path ./my_database.sqlite3
```

### 2. migrate_data.py

Script này dùng để di chuyển dữ liệu từ nguồn dữ liệu cũ sang cơ sở dữ liệu mới.

#### Cách sử dụng

Vui lòng xem tài liệu cụ thể của script này. 