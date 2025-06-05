#!/usr/bin/env python3
"""
Script test pipeline chẩn đoán độc lập
Mô phỏng đầy đủ logic API image-only-multi-turn mà không cần gọi API backend
Sử dụng database và microservices APIs
"""
import os
import sys
import json
import asyncio
import random
import time
import base64
import uuid
import sqlite3
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from PIL import Image
import io
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading
from tqdm import tqdm

# Thêm thư mục gốc vào sys.path để import các module từ app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import các service functions trực tiếp
from app.services.diagnosis_service import (
    get_first_stage_diagnosis_v3, 
    get_second_stage_diagnosis_v3
)
from app.core.logging import logger
from app.db.chromadb_service import chromadb_instance

# Environment variables cho microservices
os.environ["IMAGE_COLLECTION"] = "test-image-collection-cs"
os.environ["SQLITE_DB_PATH"] = "runtime/db3.sqlite3"
os.environ["CHROMA_HOST"] = "localhost"
os.environ["CHROMA_PORT"] = "8129"
os.environ["IMAGE_EMBEDDING_URL"] = "http://localhost:8126"
os.environ["IMAGE_EMBEDDING_API_KEY"] = "sk-proj-19Hn2k4napelkmbalkw84nb2j4k2lm6b0"

class DatabaseDiagnosisPipelineTester:
    """
    Class test pipeline chẩn đoán sử dụng database và microservices
    """
    
    def __init__(self, num_samples: int = 5):
        self.num_samples = num_samples
        self.results = []
        self.failed_samples = []
        
        # Microservices configurations
        self.image_collection = os.getenv("IMAGE_COLLECTION")
        self.sqlite_db_path = os.getenv("SQLITE_DB_PATH")
        self.chroma_host = os.getenv("CHROMA_HOST")
        self.chroma_port = os.getenv("CHROMA_PORT")
        self.embedding_url = os.getenv("IMAGE_EMBEDDING_URL")
        self.embedding_api_key = os.getenv("IMAGE_EMBEDDING_API_KEY")
        
        # Load databases
        self.load_database_connections()
        
    def load_database_connections(self):
        """Khởi tạo kết nối database"""
        logger.app_info("Initializing database connections")
        
        # SQLite connection
        try:
            self.sqlite_conn = sqlite3.connect(self.sqlite_db_path)
            self.sqlite_conn.row_factory = sqlite3.Row  # Để truy cập columns theo tên
            logger.app_info(f"SQLite connected: {self.sqlite_db_path}")
        except Exception as e:
            logger.error(f"SQLite connection failed: {str(e)}")
            self.sqlite_conn = None
        
        # ChromaDB connection sẽ sử dụng chromadb_instance đã có
        try:
            # Test ChromaDB connection
            collections = chromadb_instance.client.list_collections()
            logger.app_info(f"ChromaDB connected, collections: {[c.name for c in collections]}")
        except Exception as e:
            logger.error(f"ChromaDB connection failed: {str(e)}")
    
    def get_standard_diseases(self) -> List[Dict[str, Any]]:
        """Lấy danh sách bệnh từ domain STANDARD trong SQLite"""
        if not self.sqlite_conn:
            logger.error("SQLite connection not available")
            return []
        
        try:
            cursor = self.sqlite_conn.cursor()
            
            # Lấy domain STANDARD
            cursor.execute("""
                SELECT id FROM domains 
                WHERE domain LIKE 'STANDARD%' AND deleted_at IS NULL
                LIMIT 1
            """)
            domain_row = cursor.fetchone()
            
            if not domain_row:
                logger.error("STANDARD domain not found in database")
                return []
            
            domain_id = domain_row['id']
            logger.app_info(f"Found STANDARD domain: {domain_id}")
            
            # Lấy tất cả diseases trong domain STANDARD
            cursor.execute("""
                SELECT id, label, description 
                FROM diseases 
                WHERE domain_id = ? AND deleted_at IS NULL AND included_in_diagnosis = 1
                ORDER BY label
            """, (domain_id,))
            
            diseases = [dict(row) for row in cursor.fetchall()]
            logger.app_info(f"Found {len(diseases)} diseases in STANDARD domain")
            
            return diseases
            
        except Exception as e:
            logger.error(f"Error querying diseases: {str(e)}")
            return []
    
    def get_random_images_from_chromadb(self, num_images: int = None) -> List[Dict[str, Any]]:
        """Lấy random images từ ChromaDB collection"""
        if num_images is None:
            num_images = self.num_samples * 2  # Lấy nhiều hơn để có lựa chọn
        
        try:
            # Lấy random images từ ChromaDB
            # ChromaDB không có built-in random, nên ta sẽ lấy một batch và chọn random
            collection = chromadb_instance.image_caption_collection
            
            # Lấy tất cả IDs trước
            all_data = collection.get(
                limit=1000,  # Giới hạn để không overload
                include=["metadatas", "documents"]
            )
            
            if not all_data["ids"]:
                logger.error("No images found in ChromaDB collection")
                return []
            
            logger.app_info(f"Found {len(all_data['ids'])} images in ChromaDB")
            
            # Chọn random images
            total_images = len(all_data["ids"])
            selected_indices = random.sample(range(total_images), min(num_images, total_images))
            
            selected_images = []
            for idx in selected_indices:
                image_data = {
                    'id': all_data["ids"][idx],
                    'metadata': all_data["metadatas"][idx] if all_data["metadatas"] else {},
                    'document': all_data["documents"][idx] if all_data["documents"] else ""
                }
                selected_images.append(image_data)
            
            logger.app_info(f"Selected {len(selected_images)} random images")
            return selected_images
            
        except Exception as e:
            logger.error(f"Error getting images from ChromaDB: {str(e)}")
            return []
    
    def generate_image_description_with_embedding_api(self, image_base64: str) -> str:
        """
        Sử dụng embedding API để tạo mô tả hình ảnh
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.embedding_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "vision-description",
                "input": {
                    "image": image_base64,
                    "prompt": "Mô tả chi tiết các triệu chứng da liễu trong hình ảnh này"
                }
            }
            
            response = requests.post(
                f"{self.embedding_url}/v1/descriptions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                description = result.get("description", "Không thể tạo mô tả")
                logger.app_info(f"Generated description via embedding API: {description[:100]}...")
                return description
            else:
                logger.error(f"Embedding API error: {response.status_code} - {response.text}")
                return "Không thể tạo mô tả thông qua embedding API"
                
        except Exception as e:
            logger.error(f"Error calling embedding API: {str(e)}")
            return "Lỗi khi gọi embedding API"
    
    def create_sample_image_base64(self, width: int = 224, height: int = 224) -> str:
        """
        Tạo sample image base64 để test (vì ChromaDB chỉ chứa metadata)
        """
        try:
            # Tạo ảnh sample màu random
            color = (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))
            img = Image.new('RGB', (width, height), color)
            
            # Thêm một số noise để giống ảnh thật hơn
            pixels = np.array(img)
            noise = np.random.randint(-30, 30, pixels.shape, dtype=np.int16)
            pixels = np.clip(pixels.astype(np.int16) + noise, 0, 255).astype(np.uint8)
            img = Image.fromarray(pixels)
            
            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Error creating sample image: {str(e)}")
            return ""
    
    def select_test_samples(self) -> List[Dict[str, Any]]:
        """
        Chọn samples để test từ database
        """
        # Lấy diseases từ database
        diseases = self.get_standard_diseases()
        if not diseases:
            logger.error("No diseases found in database")
            return []
        
        # Lấy images từ ChromaDB
        images = self.get_random_images_from_chromadb(self.num_samples)
        if not images:
            logger.error("No images found in ChromaDB")
            return []
        
        # Kết hợp diseases và images
        selected_samples = []
        for i in range(min(self.num_samples, len(images))):
            # Chọn random disease
            disease = random.choice(diseases)
            image = images[i]
            
            # Tạo sample image base64 để test
            sample_image_base64 = self.create_sample_image_base64()
            
            sample = {
                'index': i,
                'disease_id': disease['id'],
                'disease_label': disease['label'],
                'disease_description': disease.get('description', ''),
                'image_id': image['id'],
                'image_metadata': image['metadata'],
                'image_document': image['document'],
                'sample_image_base64': sample_image_base64
            }
            selected_samples.append(sample)
        
        logger.app_info(f"Selected {len(selected_samples)} test samples")
        return selected_samples
    
    async def process_single_diagnosis(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Xử lý chẩn đoán cho một sample
        """
        try:
            # Tạo mô tả bằng embedding API
            logger.app_info(f"Generating description for sample {item['index']}")
            description = self.generate_image_description_with_embedding_api(item['sample_image_base64'])
            
            # Gọi trực tiếp service function thay vì API
            logger.app_info(f"Running diagnosis pipeline for sample {item['index']}")
            
            # Stage 1: First diagnosis (tương đương với không có chat_history)
            all_labels, response, chat_history = await get_first_stage_diagnosis_v3(
                image_base64=item['sample_image_base64'],
                text=description
            )
            
            # Stage 2: Follow-up question
            follow_up_question = "Bạn có thể giải thích thêm về các triệu chứng chính của bệnh này không?"
            stage2_response, updated_chat_history = await get_second_stage_diagnosis_v3(
                chat_history=chat_history,
                text=follow_up_question
            )
            
            # Trả về kết quả
            result = {
                'sample_index': item['index'],
                'database_disease_id': item['disease_id'],
                'database_disease_label': item['disease_label'],
                'chromadb_image_id': item['image_id'],
                'generated_description': description,
                'stage1_labels': all_labels,
                'stage1_response': response,
                'stage2_response': stage2_response,
                'chat_history_length': len(updated_chat_history),
                'success': True,
                'error': None
            }
            
            logger.app_info(f"Successfully processed sample {item['index']}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing sample {item['index']}: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return {
                'sample_index': item['index'],
                'database_disease_id': item.get('disease_id', ''),
                'database_disease_label': item.get('disease_label', ''),
                'chromadb_image_id': item.get('image_id', ''),
                'success': False,
                'error': str(e)
            }
    
    async def run_diagnosis_tests(self) -> Dict[str, Any]:
        """
        Chạy test pipeline chẩn đoán
        """
        logger.app_info(f"Starting database diagnosis pipeline test with {self.num_samples} samples")
        
        # Chọn samples từ database
        selected_samples = self.select_test_samples()
        
        if not selected_samples:
            return {
                'success': False,
                'error': 'No valid samples found in database',
                'results': []
            }
        
        # Xử lý từng sample
        results = []
        for i, sample in enumerate(selected_samples):
            logger.app_info(f"Processing sample {i+1}/{len(selected_samples)}")
            
            # Thêm delay để tránh overload
            if i > 0:
                await asyncio.sleep(2)
                
            result = await self.process_single_diagnosis(sample)
            results.append(result)
        
        # Tính toán thống kê
        successful_results = [r for r in results if r['success']]
        failed_results = [r for r in results if not r['success']]
        
        stats = {
            'total_samples': len(results),
            'successful_samples': len(successful_results),
            'failed_samples': len(failed_results),
            'success_rate': len(successful_results) / len(results) if results else 0
        }
        
        return {
            'success': True,
            'stats': stats,
            'results': results,
            'failed_results': failed_results
        }
    
    def save_results(self, test_results: Dict[str, Any], output_file: str = None):
        """
        Lưu kết quả test
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"tests/results/database_diagnosis_pipeline_test_{timestamp}.json"
        
        # Tạo thư mục nếu chưa có
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        # Prepare data for saving
        save_data = {
            'test_info': {
                'timestamp': datetime.now().isoformat(),
                'test_type': 'database_diagnosis_pipeline_direct_service_call',
                'num_samples': self.num_samples,
                'sqlite_db_path': self.sqlite_db_path,
                'chroma_collection': self.image_collection,
                'embedding_api_url': self.embedding_url
            },
            'stats': test_results.get('stats', {}),
            'results': []
        }
        
        # Process results for saving
        for result in test_results.get('results', []):
            save_result = result.copy()
            # Remove long base64 strings to save space
            if 'sample_image_base64' in save_result:
                save_result['sample_image_base64'] = f"[BASE64_IMAGE_{len(save_result.get('sample_image_base64', ''))}]"
            save_data['results'].append(save_result)
        
        # Save to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        
        logger.app_info(f"Test results saved to {output_file}")
        
        # Print summary
        if test_results.get('success'):
            stats = test_results['stats']
            print(f"\n{'='*60}")
            print(f"DATABASE DIAGNOSIS PIPELINE TEST SUMMARY")
            print(f"{'='*60}")
            print(f"Total samples: {stats['total_samples']}")
            print(f"Successful: {stats['successful_samples']}")
            print(f"Failed: {stats['failed_samples']}")
            print(f"Success rate: {stats['success_rate']:.2%}")
            print(f"SQLite DB: {self.sqlite_db_path}")
            print(f"ChromaDB Collection: {self.image_collection}")
            print(f"Embedding API: {self.embedding_url}")
            print(f"Results saved to: {output_file}")
            print(f"{'='*60}")
        else:
            print(f"Test failed: {test_results.get('error', 'Unknown error')}")
    
    def __del__(self):
        """Cleanup database connections"""
        if hasattr(self, 'sqlite_conn') and self.sqlite_conn:
            self.sqlite_conn.close()

async def main():
    """
    Hàm main chạy test
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Test diagnosis pipeline with database')
    parser.add_argument('--samples', type=int, default=3, help='Number of samples to test')
    parser.add_argument('--output', type=str, help='Output file path')
    
    args = parser.parse_args()
    
    # Khởi tạo tester
    tester = DatabaseDiagnosisPipelineTester(num_samples=args.samples)
    
    try:
        # Chạy test
        logger.app_info("Starting database diagnosis pipeline test")
        test_results = await tester.run_diagnosis_tests()
        
        # Lưu kết quả
        tester.save_results(test_results, args.output)
        
        return test_results['stats']['success_rate'] > 0.5 if test_results.get('success') else False
        
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Chạy test
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 