# Query System API

Hệ thống API cho xử lý và phân tích dữ liệu y tế.

## Yêu cầu

- Docker
- Docker Compose (tùy chọn)

## Cách sử dụng Docker

### Build và Push Docker Image

Sử dụng script `build_and_push.sh` để build và push Docker image:

```bash
# Cấp quyền thực thi cho script
chmod +x build_and_push.sh

# Sử dụng với tham số mặc định
./build_and_push.sh

# Hoặc với tham số tùy chỉnh
./build_and_push.sh your_dockerhub_username query_system v1.0

# Nếu muốn tự động xóa image sau khi push để giải phóng bộ nhớ
./build_and_push.sh your_dockerhub_username query_system v1.0 clean
```

### Chạy Docker Container

```bash
# Chạy với cấu hình mặc định
docker run -p 8123:8123 yourusername/query_system:latest

# Chạy với cấu hình tùy chỉnh host và port
docker run -p 9000:9000 yourusername/query_system:latest --host 0.0.0.0 --port 9000

# Chạy với chế độ reload và số lượng workers tùy chỉnh
docker run -p 8123:8123 -v $(pwd):/app yourusername/query_system:latest --reload --workers 4
```

### Sử dụng Docker Compose

Tạo file `docker-compose.yml` với nội dung:

```yaml
version: '3.8'

services:
  api:
    image: yourusername/query_system:latest
    ports:
      - "8123:8123"
    command: ["--host", "0.0.0.0", "--port", "8123", "--workers", "2"]
    volumes:
      - ./chroma_data:/app/chroma_data
    restart: unless-stopped
```

Sau đó chạy:

```bash
docker-compose up -d
```

### Xóa Docker Image

Nếu bạn muốn xóa Docker image cục bộ để giải phóng bộ nhớ (sau khi đã push lên Docker Hub):

```bash
# Xóa image thủ công
docker rmi yourusername/query_system:latest

# Hoặc sử dụng tùy chọn "clean" trong script build_and_push.sh
./build_and_push.sh yourusername query_system latest clean
```

### Dọn dẹp Docker Resources

Sử dụng script `cleanup_docker.sh` để dọn dẹp các Docker resources không sử dụng:

```bash
# Cấp quyền thực thi cho script
chmod +x cleanup_docker.sh

# Dọn dẹp cơ bản (sẽ hỏi trước khi xóa containers và volumes)
./cleanup_docker.sh

# Dọn dẹp toàn diện (xóa tất cả containers đã dừng, dangling images, networks, volumes không sử dụng và build cache)
./cleanup_docker.sh --all
```

Script này sẽ giúp bạn:
- Xóa các dangling images (các image không còn được sử dụng)
- Xóa các container đã dừng
- Xóa các network không sử dụng
- Xóa các volume không sử dụng
- Xóa build cache (khi sử dụng tùy chọn `--all`)

## API Endpoints

- `GET /`: Health check
- `POST /diagnosis`: Chẩn đoán từ text và ảnh
- `POST /get-context`: Lấy thông tin ngữ cảnh từ text và ảnh

## Tham số Command Line

Khi chạy container, bạn có thể chỉ định các tham số sau:

- `--host`: Host để bind server (mặc định: 0.0.0.0)
- `--port`: Port để bind server (mặc định: 8123)
- `--reload`: Bật chế độ tự động reload khi code thay đổi
- `--workers`: Số lượng worker processes (mặc định: 1)

## Tổ chức lại cấu trúc dự án theo mô hình FastAPI chuẩn

Sau đây là cấu trúc thư mục được đề xuất để tổ chức lại dự án theo mô hình FastAPI tiêu chuẩn:

```
medical-diagnosis-api/
│
├── app/                          # Thư mục chính chứa mã nguồn ứng dụng
│   ├── __init__.py               # Khởi tạo package
│   ├── main.py                   # Điểm vào chính của ứng dụng FastAPI
│   ├── core/                     # Cấu hình cốt lõi và tiện ích
│   │   ├── __init__.py
│   │   ├── config.py             # Cấu hình ứng dụng (biến môi trường, settings)
│   │   ├── logging.py            # Cấu hình logging
│   │   └── utils.py              # Các tiện ích dùng chung
│   │
│   ├── api/                      # API endpoints
│   │   ├── __init__.py
│   │   ├── routes/               # Các router
│   │   │   ├── __init__.py
│   │   │   ├── diagnosis.py      # Endpoints liên quan đến chẩn đoán
│   │   │   └── health.py         # Health check endpoints
│   │   └── dependencies.py       # Các dependency cho API
│   │
│   ├── models/                   # Pydantic models cho API
│   │   ├── __init__.py
│   │   ├── request.py            # Models cho request
│   │   ├── response.py           # Models cho response
│   │   └── domain.py             # Domain models
│   │
│   ├── services/                 # Service layer
│   │   ├── __init__.py
│   │   ├── diagnosis_service.py  # Logic chẩn đoán
│   │   ├── llm_service.py        # Service LLM 
│   │   ├── image_service.py      # Service xử lý hình ảnh (MedImageInsights)
│   │   └── database_service.py   # Service truy vấn database
│   │
│   ├── db/                       # Database layer
│   │   ├── __init__.py
│   │   ├── chromadb.py           # ChromaDB service
│   │   └── neo4j.py              # Neo4j service
│   │
│   └── constants/                # Các hằng số và enums
│       ├── __init__.py
│       └── enums.py              # Enum definitions
│
├── runtime/                      # Thư mục chứa dữ liệu runtime
│   ├── chroma_data/              # Dữ liệu ChromaDB
│   └── models/                   # Thư mục chứa models AI
│       └── MedImageInsights/     # MedImageInsights model
│
├── scripts/                      # Scripts tiện ích
│   ├── migrate_data.py           # Script để migrate dữ liệu
│   └── test_api.py               # Script để test API
│
├── tests/                        # Unit tests
│   ├── __init__.py
│   ├── test_api.py
│   └── test_services.py
│
├── .env.example                  # Template biến môi trường
├── .gitignore                    # Git ignore file
├── docker-compose.yml            # Docker Compose configuration
├── Dockerfile                    # Docker configuration
├── requirements.txt              # Dependencies
└── README.md                     # Documentation
```

### Hướng dẫn chuyển đổi cấu trúc dự án

1. Tạo cấu trúc thư mục mới:
```bash
mkdir -p app/{core,api/routes,models,services,db,constants}
mkdir -p runtime/{chroma_data,models/MedImageInsights}
mkdir -p scripts tests
```

2. Di chuyển các file hiện tại sang cấu trúc mới:

- `api_app.py` → `app/main.py` (chỉnh sửa imports)
- `constants.py` → `app/models/domain.py` và `app/constants/enums.py`
- `diagnosis_logic.py` → `app/services/diagnosis_service.py`
- `chromadb_service.py` → `app/db/chromadb.py`
- `neo4j_service.py` → `app/db/neo4j.py`
- `gemini_llm_service.py` → `app/services/llm_service.py`
- `embedding_service.py` → `app/services/image_service.py`
- `logging_utils.py` → `app/core/logging.py`
- `utils.py` → `app/core/utils.py`
- MedImageInsights (move to) → `runtime/models/MedImageInsights`

3. Tạo các file cần thiết mới:

- `app/__init__.py`
- `app/api/__init__.py`
- `app/api/routes/__init__.py`
- `app/api/routes/diagnosis.py` (endpoints từ api_app.py)
- `app/api/routes/health.py` (health check endpoint)
- `app/core/config.py` (settings từ .env)
- `app/models/request.py` (DiagnosisRequest)
- `app/models/response.py` (DiagnosisResponse)

4. Cập nhật imports trong các file để phù hợp với cấu trúc mới.

5. Cập nhật docker-compose.yml và Dockerfile để phản ánh cấu trúc thư mục mới.

### Lợi ích của cấu trúc mới

1. **Tách biệt mối quan tâm**: Mỗi thành phần có vai trò và trách nhiệm rõ ràng
2. **Dễ mở rộng**: Dễ dàng thêm các endpoints mới, services mới mà không ảnh hưởng đến code hiện tại
3. **Dễ bảo trì**: Cấu trúc rõ ràng giúp dễ dàng tìm và sửa lỗi
4. **Dễ test**: Cấu trúc module hóa giúp viết unit tests dễ dàng hơn
5. **Tài liệu rõ ràng**: Cấu trúc tuân theo các tiêu chuẩn FastAPI, giúp người mới dễ hiểu

### Lazy Loading

Với cấu trúc mới này, chúng ta vẫn giữ được cơ chế lazy loading cho MedImageInsights:

- `app/services/image_service.py` chỉ được import khi cần thiết trong `app/db/chromadb.py`
- Model nặng chỉ được load khi có request liên quan đến hình ảnh 