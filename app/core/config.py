import os
from typing import Dict, Any, Optional, List
from pydantic_settings import BaseSettings
from pydantic import field_validator
from dotenv import load_dotenv

# Tải các biến môi trường từ file .env nếu tồn tại
load_dotenv(override=True)

class Settings(BaseSettings):
    # Thông tin cơ bản
    API_PREFIX: str = "/api"
    APP_NAME: str = "Medical Diagnosis API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    # Cấu hình server
    HOST: str = "0.0.0.0"
    PORT: int = 8123
    RELOAD: bool = False
    WORKERS: int = 1
    
    # Ngrok configuration
    NGROK_ENABLED: bool = False
    NGROK_AUTHTOKEN: Optional[str] = None
    NGROK_URL: Optional[str] = None
    
    # Đường dẫn thư mục
    CHROMA_DATA_PATH: str = "runtime/chroma_data"
    
    # LLM API Keys và cấu hình
    GEMINI_API_KEY: Optional[str] = None
    
    # Neo4j configuration
    NEO4J_URI: Optional[str] = None
    NEO4J_USERNAME: Optional[str] = None
    NEO4J_PASSWORD: Optional[str] = None
    NEO4J_DATABASE: str = "neo4j"

    # Embedding API Keys và cấu hình
    EMBEDDING_URL: Optional[str] = None
    EMBEDDING_API_KEY: Optional[str] = None
    EMBEDDING_MODEL: str = "bge-m3"

    IMAGE_EMBEDDING_URL: Optional[str] = None
    IMAGE_EMBEDDING_API_KEY: Optional[str] = None
    
    # SQLite configuration
    SQLITE_DB_PATH: str = "runtime/db.sqlite3"
    SQLITE_ECHO: bool = False
    
    # Image configuration
    IMAGE_BASE_URL: str = "runtime/image/"

    # Hugging Face configuration
    HF_TOKEN: Optional[str] = None

    # Collection name
    ENTITY_COLLECTION: str = "entity-collection-ip"
    DOCUMENT_COLLECTION: str = "document-collection-ip"
    IMAGE_COLLECTION: str = "image-caption-collection-ip"

    @field_validator("GEMINI_API_KEY", "NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD", "EMBEDDING_URL", "EMBEDDING_API_KEY")
    def validate_not_none(cls, v, info):
        if v is None:
            raise ValueError(f"{info.field_name} must be set in environment variables")
        return v
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True
    }

settings = Settings() 