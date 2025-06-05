import os
import json
from typing import Dict, Any, Optional, List, Union
from pydantic_settings import BaseSettings
from pydantic import field_validator, model_validator
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
    WORKERS: int = 4
    
    # Đường dẫn thư mục
    CHROMA_DATA_PATH: str = "runtime/chroma_data"
    
    # LLM API Keys và cấu hình
    GEMINI_API_KEY: Optional[str] = None  # Backward compatibility - deprecated
    GEMINI_API_KEYS: Optional[Union[str, List[str]]] = None  # New: Multiple API keys
    GEMINI_MODELS: Union[str, List[str]] = '["gemini-2.0-flash","gemini-2.0-pro","gemini-1.5-pro","gemini-1.5-flash"]'
    
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

    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8129

    # Collection name
    ENTITY_COLLECTION: str = "entity-collection-ip"
    DOCUMENT_COLLECTION: str = "document-collection-ip"
    IMAGE_COLLECTION: str = "image-caption-collection-ip"

    @field_validator("GEMINI_API_KEY", "NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD", "EMBEDDING_URL", "EMBEDDING_API_KEY")
    def validate_not_none(cls, v, info):
        if v is None and info.field_name != "GEMINI_API_KEY":  # GEMINI_API_KEY có thể None nếu dùng GEMINI_API_KEYS
            raise ValueError(f"{info.field_name} must be set in environment variables")
        return v
    
    @field_validator("GEMINI_API_KEYS")
    def validate_gemini_api_keys(cls, v):
        """
        Parse GEMINI_API_KEYS từ string hoặc list thành List[str]
        """
        # Nếu GEMINI_API_KEYS không được set, return None để fallback sau
        if v is None:
            return None
            
        if isinstance(v, list):
            if not v or len(v) == 0:
                raise ValueError("GEMINI_API_KEYS must contain at least one API key")
            return v
        
        if isinstance(v, str):
            # Thử parse như JSON trước
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
                    if not parsed or len(parsed) == 0:
                        raise ValueError("GEMINI_API_KEYS must contain at least one API key")
                    return parsed
                else:
                    raise ValueError("GEMINI_API_KEYS JSON must be a list of strings")
            except json.JSONDecodeError:
                # Nếu không phải JSON, thử parse như comma-separated
                api_keys = [key.strip() for key in v.split(',') if key.strip()]
                if not api_keys or len(api_keys) == 0:
                    raise ValueError("GEMINI_API_KEYS must contain at least one API key")
                return api_keys
        
        raise ValueError("GEMINI_API_KEYS must be a JSON string, comma-separated string, or list")

    @model_validator(mode='after')
    def validate_api_keys_fallback(self):
        """Fallback logic: Nếu GEMINI_API_KEYS None, dùng GEMINI_API_KEY"""
        if self.GEMINI_API_KEYS is None:
            if self.GEMINI_API_KEY is not None:
                self.GEMINI_API_KEYS = [self.GEMINI_API_KEY]
            else:
                raise ValueError("Either GEMINI_API_KEYS or GEMINI_API_KEY must be set")
        return self

    @field_validator("GEMINI_MODELS")
    def validate_gemini_models(cls, v):
        """
        Parse GEMINI_MODELS từ string hoặc list thành List[str]
        Hỗ trợ:
        - JSON string từ env: '["model1","model2"]' 
        - Comma-separated từ env: "model1,model2,model3"
        - List trực tiếp: ["model1", "model2"]
        """
        if isinstance(v, list):
            # Nếu đã là list, validate và return
            if not v or len(v) == 0:
                raise ValueError("GEMINI_MODELS must contain at least one model")
            return v
        
        if isinstance(v, str):
            # Thử parse như JSON trước
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
                    if not parsed or len(parsed) == 0:
                        raise ValueError("GEMINI_MODELS must contain at least one model")
                    return parsed
                else:
                    raise ValueError("GEMINI_MODELS JSON must be a list of strings")
            except json.JSONDecodeError:
                # Nếu không phải JSON, thử parse như comma-separated
                models = [model.strip() for model in v.split(',') if model.strip()]
                if not models or len(models) == 0:
                    raise ValueError("GEMINI_MODELS must contain at least one model")
                return models
        
        raise ValueError("GEMINI_MODELS must be a JSON string, comma-separated string, or list")
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True
    }

settings = Settings() 