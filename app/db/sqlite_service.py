import os
import sqlite3
from pathlib import Path
from typing import Optional, Union, Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy import create_engine, text, MetaData, Table, Column, String, Boolean, DateTime, ForeignKey, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings
from app.core.logging import logger

# Tạo engine SQLAlchemy
DATABASE_URL = f"sqlite:///{settings.SQLITE_DB_PATH}"
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False},
    echo=settings.SQLITE_ECHO
)

# Tạo base class cho các model
Base = declarative_base()

# Tạo session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    Dependency function để lấy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Khởi tạo database từ schema SQL
    """
    # Đảm bảo thư mục chứa database tồn tại
    os.makedirs(os.path.dirname(settings.SQLITE_DB_PATH), exist_ok=True)
    
    # Kiểm tra xem file database đã tồn tại chưa
    db_exists = os.path.exists(settings.SQLITE_DB_PATH)
    
    if not db_exists:
        logger.app_info(f"Initializing SQLite database at {settings.SQLITE_DB_PATH}")
        # Tạo database từ schema.sql
        with sqlite3.connect(settings.SQLITE_DB_PATH) as conn:
            with open("schema.sql", "r") as f:
                conn.executescript(f.read())
            conn.commit()
        logger.app_info("Database successfully initialized")
    else:
        logger.app_info(f"Database already exists at {settings.SQLITE_DB_PATH}")
    
    # Tạo các bảng trong SQLAlchemy (nếu chưa tồn tại)
    Base.metadata.create_all(bind=engine)

def execute_query(query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Thực thi câu truy vấn SQL trực tiếp và trả về kết quả
    """
    with engine.connect() as connection:
        result = connection.execute(text(query), params or {})
        return [dict(row._mapping) for row in result]

def execute_script(script: str):
    """
    Thực thi script SQL
    """
    with sqlite3.connect(settings.SQLITE_DB_PATH) as conn:
        conn.executescript(script)
        conn.commit() 