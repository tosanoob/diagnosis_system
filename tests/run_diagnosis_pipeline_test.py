#!/usr/bin/env python3
"""
Script runner để chạy database diagnosis pipeline test đơn giản
"""
import os
import sys
import asyncio
from pathlib import Path

# Thêm thư mục gốc vào sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_diagnosis_pipeline import DatabaseDiagnosisPipelineTester

async def run_simple_test():
    """
    Chạy test đơn giản với 2 samples từ database
    """
    print("🚀 Starting Database Diagnosis Pipeline Test")
    print("="*55)
    
    # Kiểm tra environment variables
    required_envs = [
        "IMAGE_COLLECTION", "SQLITE_DB_PATH", "CHROMA_HOST", 
        "CHROMA_PORT", "IMAGE_EMBEDDING_URL", "IMAGE_EMBEDDING_API_KEY"
    ]
    
    missing_envs = []
    for env_var in required_envs:
        if not os.getenv(env_var):
            missing_envs.append(env_var)
    
    if missing_envs:
        print(f"⚠️  Missing environment variables: {', '.join(missing_envs)}")
        print("Using default values for testing...")
    
    # Khởi tạo tester với 2 samples
    tester = DatabaseDiagnosisPipelineTester(num_samples=2)
    
    try:
        # Chạy test
        test_results = await tester.run_diagnosis_tests()
        
        # Lưu kết quả
        tester.save_results(test_results)
        
        return test_results.get('success', False)
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(run_simple_test())
    
    if success:
        print("✅ Database test completed successfully!")
    else:
        print("❌ Database test failed!")
    
    sys.exit(0 if success else 1) 