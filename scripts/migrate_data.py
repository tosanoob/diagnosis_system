#!/usr/bin/env python3
"""
Script di chuyển dữ liệu từ cấu trúc cũ sang cấu trúc mới
"""
import shutil
import os
from pathlib import Path
import argparse
import sys

# Thêm thư mục gốc vào sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(script_dir, ".."))
sys.path.insert(0, root_dir)

# Cấu hình mapping file/directory
FILE_MAPPING = {
    "api_app.py": "app/main.py",
    "chromadb_service.py": "app/db/chromadb.py",
    "neo4j_service.py": "app/db/neo4j.py",
    "llm_service.py": "app/services/llm_service.py",
    "gemini_llm_service.py": "app/services/llm_service.py",
    "embedding_service.py": "app/services/image_service.py",
    "utils.py": "app/core/utils.py"
}

DIR_MAPPING = {
    "chroma_data": "runtime/chroma_data",
    "MedImageInsights": "runtime/models/MedImageInsights"
}

def copy_file(src, dest):
    """Copy file from source to destination"""
    print(f"Copying {src} to {dest}")
    dest_dir = os.path.dirname(dest)
    os.makedirs(dest_dir, exist_ok=True)
    shutil.copy2(src, dest)

def copy_dir(src, dest):
    """Copy directory from source to destination"""
    print(f"Copying directory {src} to {dest}")
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(src, dest)

def migrate_data():
    """Migrate data from old structure to new structure"""
    # Kiểm tra thư mục hiện tại là thư mục gốc
    if not os.path.exists("app") or not os.path.exists("runtime"):
        print("Error: Please run this script from the project root directory")
        sys.exit(1)
        
    # Di chuyển files
    for src, dest in FILE_MAPPING.items():
        if os.path.exists(src):
            copy_file(src, dest)
        else:
            print(f"Warning: Source file {src} not found")
            
    # Di chuyển directories
    for src, dest in DIR_MAPPING.items():
        if os.path.exists(src):
            copy_dir(src, dest)
        else:
            print(f"Warning: Source directory {src} not found")
    
    print("Migration completed successfully!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate data from old structure to new structure")
    parser.add_argument("--force", action="store_true", help="Force migration even if destination files exist")
    
    args = parser.parse_args()
    
    if args.force:
        print("Forcing migration...")
        
    migrate_data() 