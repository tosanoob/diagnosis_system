# API Testing Framework

Framework kiểm thử tự động cho Medical Diagnosis API.

## Cấu trúc thư mục

```
tests/
├── README.md              # Tài liệu hướng dẫn này
├── __init__.py            # File khởi tạo package
├── test_runner.py         # Script chạy tất cả các test
├── test_health.py         # Test endpoints health
├── test_diagnosis.py      # Test endpoints diagnosis 
├── test_database.py       # Test endpoints  // deprecated
├── test_domain.py         # Test endpoints domain
├── test_auth.py           # Test endpoints authentication
└── results/               # Thư mục chứa kết quả test
    ├── health_test_result.json
    ├── diagnosis_test_result.json
    ├── database_test_result.json
    ├── domain_test_result.json
    ├── auth_test_result.json
    └── test_run_summary.json
```

## Cách sử dụng

### Cài đặt dependencies

```bash
pip install requests
```

### Chạy tất cả các test

```bash
# Sử dụng API endpoint mặc định (http://localhost:8100/api)
python tests/test_runner.py

# Chỉ định API endpoint
python tests/test_runner.py --api-url http://localhost:8123/api
```

### Chạy test cụ thể

```bash
# Chạy test cho health endpoints
python tests/test_runner.py --test-file test_health.py

# Chạy test cho diagnosis endpoints
python tests/test_runner.py --test-file test_diagnosis.py

# Chạy test cho domain endpoints
python tests/test_runner.py --test-file test_domain.py

# Chạy test cho authentication
python tests/test_runner.py --test-file test_auth.py
```

### Chạy test với ngrok

```bash
# Sử dụng URL ngrok
python tests/test_runner.py --api-url https://your-ngrok-url.ngrok-free.app/api
```

## Các tính năng

1. **Tự động ghi log kết quả test**: Mọi test run đều được lưu vào thư mục `results/`
2. **Test API độc lập**: Không có phụ thuộc vào môi trường cục bộ
3. **Test các tác vụ CRUD đầy đủ**: Tạo, đọc, cập nhật, xóa
4. **Báo cáo tổng hợp**: Hiển thị tóm tắt kết quả sau mỗi lần chạy

## Các API endpoint được test

### Health
- `GET /health`: Kiểm tra trạng thái hoạt động của API

### Authentication
- `POST /auth/login`: Đăng nhập người dùng và lấy token
- `POST /auth/logout`: Đăng xuất (vô hiệu hóa token)

### Diagnosis
- `POST /diagnosis/analyze`: Chẩn đoán dựa trên text và/hoặc ảnh
- `POST /diagnosis/context`: Lấy thông tin liên quan đến bệnh
- `POST /diagnosis/image-only`: Chẩn đoán chỉ dựa vào ảnh

### Domain
- `GET /domains`: Lấy danh sách lĩnh vực y tế
- `POST /domains`: Tạo lĩnh vực y tế mới
- `GET /domains/{id}`: Lấy thông tin chi tiết lĩnh vực y tế
- `PUT /domains/{id}`: Cập nhật lĩnh vực y tế
- `DELETE /domains/{id}`: Xóa lĩnh vực y tế

### Database
- `GET /db/diseases`: Lấy danh sách bệnh
- `GET /db/articles`: Lấy danh sách bài viết
- `POST /db/diseases`: Tạo bệnh mới
- `PUT /db/diseases/{id}`: Cập nhật bệnh
- `DELETE /db/diseases/{id}`: Xóa bệnh
- `GET /db/roles`: Lấy danh sách vai trò
- `GET /db/users`: Lấy danh sách người dùng

## Các lưu ý khi mở rộng

1. **Thêm test mới**: Tạo file `test_*.py` trong thư mục `tests/` và thực hiện kiểm thử
2. **Sử dụng lại cấu trúc chung**: Mỗi test file nên có cùng cấu trúc với các test hiện tại
3. **Sửa đổi biến môi trường**: Thay đổi `API_BASE_URL` để test trên các môi trường khác nhau 