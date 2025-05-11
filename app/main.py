from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse
import uvicorn
import argparse
import os
from pyngrok import ngrok, conf
from app.api.routes import router
from app.core.config import settings
from app.core.logging import logger, setup_logging
from app.db.sqlite_service import init_db, get_db
from app.services import image_management_service

def create_application() -> FastAPI:
    """
    Tạo và cấu hình ứng dụng FastAPI
    """
    application = FastAPI(
        title=settings.APP_NAME,
        description="API cung cấp dịch vụ chẩn đoán da liễu tự động",
        version=settings.APP_VERSION,
        docs_url="/docs"
    )
    
    # Cấu hình CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Thêm router
    application.include_router(router, prefix=settings.API_PREFIX)
    
    return application

app = create_application()

# Middleware để log request giúp debug vấn đề ngrok
@app.middleware("http")
async def request_logger_middleware(request: Request, call_next):
    # Ghi log thông tin request
    client_host = request.client.host if request.client else "Unknown"
    logger.app_info(f"Request from: {client_host}, path: {request.url.path}, method: {request.method}")
    
    # Log một số header quan trọng
    if "x-forwarded-for" in request.headers:
        logger.app_info(f"X-Forwarded-For: {request.headers['x-forwarded-for']}")
    if "host" in request.headers:
        logger.app_info(f"Host header: {request.headers['host']}")
    
    response = await call_next(request)
    logger.app_info(f"Response status: {response.status_code}")
    
    return response

@app.on_event("startup")
async def startup_event():
    """
    Xử lý các tác vụ khi khởi động ứng dụng
    """
    logger.app_info(f"Starting {settings.APP_NAME} version {settings.APP_VERSION}")
    logger.app_info(f"Debug mode: {settings.DEBUG}")
    
    # Khởi tạo SQLite database
    init_db()
    
    # Đảm bảo thư mục lưu trữ hình ảnh tồn tại
    image_root_dir = "runtime/image"
    object_types = ["disease", "article", "clinic"]
    for object_type in object_types:
        dir_path = os.path.join(image_root_dir, object_type)
        os.makedirs(dir_path, exist_ok=True)
        logger.app_info(f"Ensured image directory exists: {dir_path}")
    
    # Mount thư mục hình ảnh để phục vụ trực tiếp
    app.mount("/static/images", StaticFiles(directory=image_root_dir), name="images")
    logger.app_info(f"Mounted image directory at /static/images")
    
    # Khởi tạo image usages
    db_generator = get_db()
    db = next(db_generator)
    try:
        await image_management_service.init_image_usages(db)
        logger.app_info("Image usages initialized")
    except Exception as e:
        logger.error(f"Error initializing image usages: {str(e)}")
    finally:
        db_generator.close()
    
    # Set up ngrok tunnel if enabled
    if settings.NGROK_ENABLED:
        try:
            # Set authtoken if provided
            if settings.NGROK_AUTHTOKEN:
                conf.get_default().auth_token = settings.NGROK_AUTHTOKEN
                logger.app_info("Ngrok authtoken set")
            
            public_url = ngrok.connect(addr=f"{settings.PORT}", bind_tls=True, hostname=settings.NGROK_URL)
            logger.app_info(f"Ngrok tunnel established at: {public_url}")
            logger.app_info(f"Tunneling traffic from {public_url} -> localhost:{settings.PORT}")
            
        except Exception as e:
            logger.error(f"Failed to establish ngrok tunnel: {str(e)}")
    
@app.on_event("shutdown")
async def shutdown_event():
    """
    Xử lý các tác vụ khi đóng ứng dụng
    """
    # Close ngrok tunnels when app shuts down
    if settings.NGROK_ENABLED:
        try:
            ngrok.kill()
            logger.app_info("Ngrok tunnels closed")
        except Exception as e:
            logger.error(f"Error closing ngrok tunnels: {str(e)}")
            
    logger.app_info(f"Shutting down {settings.APP_NAME}")

if __name__ == "__main__":
    # Cấu hình command line arguments
    parser = argparse.ArgumentParser(description="Khởi chạy API service")
    parser.add_argument("--host", type=str, default=settings.HOST, help="Host để bind server")
    parser.add_argument("--port", type=int, default=settings.PORT, help="Port để bind server")
    parser.add_argument("--reload", action="store_true", help="Bật chế độ tự động reload khi code thay đổi")
    parser.add_argument("--workers", type=int, default=settings.WORKERS, help="Số lượng worker processes")
    parser.add_argument("--log-file", type=str, default="logs/app.log", help="File log")
    parser.add_argument("--enable-ngrok", action="store_true", help="Enable ngrok tunnel")
    
    args = parser.parse_args()
    
    # Set ngrok enabled flag from command line argument
    settings.NGROK_ENABLED = args.enable_ngrok
    settings.PORT = args.port
    settings.HOST = args.host
    
    # Cấu hình logging
    setup_logging(log_file=args.log_file)
    
    # Khởi chạy ứng dụng FastAPI với Uvicorn
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers
    ) 