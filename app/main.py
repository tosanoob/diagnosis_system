from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import argparse
from app.api.routes import router
from app.core.config import settings
from app.core.logging import logger, setup_logging

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

@app.on_event("startup")
async def startup_event():
    """
    Xử lý các tác vụ khi khởi động ứng dụng
    """
    logger.info(f"Starting {settings.APP_NAME} version {settings.APP_VERSION}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
@app.on_event("shutdown")
async def shutdown_event():
    """
    Xử lý các tác vụ khi đóng ứng dụng
    """
    logger.info(f"Shutting down {settings.APP_NAME}")

if __name__ == "__main__":
    # Cấu hình command line arguments
    parser = argparse.ArgumentParser(description="Khởi chạy API service")
    parser.add_argument("--host", type=str, default=settings.HOST, help="Host để bind server")
    parser.add_argument("--port", type=int, default=settings.PORT, help="Port để bind server")
    parser.add_argument("--reload", action="store_true", help="Bật chế độ tự động reload khi code thay đổi")
    parser.add_argument("--workers", type=int, default=settings.WORKERS, help="Số lượng worker processes")
    parser.add_argument("--log-file", type=str, default="logs/app.log", help="File log")
    
    args = parser.parse_args()
    
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