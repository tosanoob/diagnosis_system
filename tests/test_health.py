import requests
import json
import os
from pathlib import Path

# Cấu hình API endpoint
BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8100/api")

def test_health_check():
    """
    Test endpoint kiểm tra trạng thái hoạt động của API
    """
    # Gửi request
    response = requests.get(f"{BASE_URL}/health")
    
    # Kiểm tra status code
    assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}"
    
    # Kiểm tra cấu trúc response
    data = response.json()
    assert "status" in data, "Response should contain status field"
    assert "version" in data, "Response should contain version field"
    assert "components" in data, "Response should contain components field"
    
    # Kiểm tra giá trị
    assert data["status"] == "ok", f"Expected status 'ok' but got {data['status']}"
    
    # Kiểm tra components
    assert "system" in data["components"], "Components should contain system information"
    assert "paths" in data["components"], "Components should contain paths information"
    
    print("✅ Health check test passed")

if __name__ == "__main__":
    # Tạo thư mục để lưu kết quả
    Path("tests/results").mkdir(parents=True, exist_ok=True)
    
    # Chạy test
    try:
        test_health_check()
        
        # Lưu kết quả test
        result = {
            "test": "Health Check",
            "status": "passed",
            "timestamp": str(Path(__file__).stat().st_mtime)
        }
        
        with open("tests/results/health_test_result.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
            
        print("✅ All health tests passed!")
    except Exception as e:
        # Lưu lỗi
        result = {
            "test": "Health Check",
            "status": "failed",
            "error": str(e),
            "timestamp": str(Path(__file__).stat().st_mtime)
        }
        
        with open("tests/results/health_test_result.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
            
        print(f"❌ Test failed: {str(e)}")
        raise 