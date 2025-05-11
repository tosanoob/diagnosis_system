import requests
import json
import os
import base64
from pathlib import Path
from typing import Optional

# Cấu hình API endpoint
BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8100/api")

def load_test_image(image_path: str = None) -> Optional[str]:
    """
    Tải ảnh test và mã hóa base64
    """
    # Sử dụng ảnh mặc định nếu không có đường dẫn
    if not image_path:
        image_path = "test_image.jpg"
    
    # Kiểm tra file tồn tại
    if not Path(image_path).exists():
        print(f"Warning: Test image not found at {image_path}")
        return None
    
    # Đọc và mã hóa ảnh
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

def test_diagnosis_text_only():
    """
    Test endpoint chẩn đoán chỉ với text
    """
    # Dữ liệu test
    payload = {
        "text": "Da bị ngứa, đỏ và có nhiều mảng tròn có viền đỏ và trung tâm hơi nhạt, xuất hiện trên cánh tay và ngực",
        "image_base64": None
    }
    
    # Gửi request
    response = requests.post(f"{BASE_URL}/diagnosis/analyze", json=payload)
    
    # Kiểm tra status code
    assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}"
    
    # Kiểm tra cấu trúc response
    data = response.json()
    assert "labels" in data, "Response should contain labels field"
    assert "response" in data, "Response should contain response field"
    
    # Kiểm tra dữ liệu trả về
    assert isinstance(data["labels"], list), "Labels should be a list"
    assert len(data["labels"]) > 0, "Labels list should not be empty"
    assert isinstance(data["response"], str), "Response should be a string"
    assert len(data["response"]) > 0, "Response string should not be empty"
    
    print("✅ Text-only diagnosis test passed")

def test_diagnosis_image_only():
    """
    Test endpoint chẩn đoán chỉ với ảnh
    """
    # Tải ảnh test
    image_base64 = load_test_image()
    if not image_base64:
        print("⚠️ Skipping image-only diagnosis test due to missing test image")
        return
    
    # Dữ liệu test
    payload = {
        "text": None,
        "image_base64": image_base64
    }
    
    # Gửi request
    response = requests.post(f"{BASE_URL}/diagnosis/image-only", json=payload)
    
    # Kiểm tra status code
    assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}"
    
    # Kiểm tra cấu trúc response
    data = response.json()
    assert "labels" in data, "Response should contain labels field"
    assert "documents" in data, "Response should contain documents field"
    
    # Kiểm tra dữ liệu trả về
    assert isinstance(data["labels"], list), "Labels should be a list"
    assert len(data["labels"]) > 0, "Labels list should not be empty"
    
    print("✅ Image-only diagnosis test passed")

def test_get_context():
    """
    Test endpoint lấy context với text
    """
    # Dữ liệu test
    payload = {
        "text": "Nấm da, hắc lào",
        "image_base64": None
    }
    
    # Gửi request
    response = requests.post(f"{BASE_URL}/diagnosis/context", json=payload)
    
    # Kiểm tra status code
    assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}"
    
    # Kiểm tra cấu trúc response
    data = response.json()
    assert "labels" in data, "Response should contain labels field"
    assert "documents" in data, "Response should contain documents field"
    
    # Kiểm tra dữ liệu trả về
    assert isinstance(data["labels"], list), "Labels should be a list"
    assert isinstance(data["documents"], list), "Documents should be a list"
    
    print("✅ Get context test passed")

def test_combined_diagnosis():
    """
    Test endpoint chẩn đoán với cả text và ảnh
    """
    # Tải ảnh test
    image_base64 = load_test_image()
    if not image_base64:
        print("⚠️ Skipping combined diagnosis test due to missing test image")
        return
    
    # Dữ liệu test
    payload = {
        "text": "Da bị ngứa, đỏ và có nhiều vết tròn",
        "image_base64": image_base64
    }
    
    # Gửi request
    response = requests.post(f"{BASE_URL}/diagnosis/analyze", json=payload)
    
    # Kiểm tra status code
    assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}"
    
    # Kiểm tra cấu trúc response
    data = response.json()
    assert "labels" in data, "Response should contain labels field"
    assert "response" in data, "Response should contain response field"
    
    print("✅ Combined diagnosis test passed")

if __name__ == "__main__":
    # Tạo thư mục để lưu kết quả
    Path("tests/results").mkdir(parents=True, exist_ok=True)
    
    # Chạy tests
    results = {}
    
    try:
        # Test chẩn đoán chỉ với text
        test_diagnosis_text_only()
        results["text_only_diagnosis"] = {"status": "passed"}
    except Exception as e:
        results["text_only_diagnosis"] = {"status": "failed", "error": str(e)}
        print(f"❌ Text-only diagnosis test failed: {str(e)}")
    
    try:
        # Test lấy context
        test_get_context()
        results["get_context"] = {"status": "passed"}
    except Exception as e:
        results["get_context"] = {"status": "failed", "error": str(e)}
        print(f"❌ Get context test failed: {str(e)}")
    
    try:
        # Test chẩn đoán chỉ với ảnh
        test_diagnosis_image_only()
        results["image_only_diagnosis"] = {"status": "passed"}
    except Exception as e:
        results["image_only_diagnosis"] = {"status": "failed", "error": str(e)}
        print(f"❌ Image-only diagnosis test failed: {str(e)}")
    
    try:
        # Test chẩn đoán với cả text và ảnh
        test_combined_diagnosis()
        results["combined_diagnosis"] = {"status": "passed"}
    except Exception as e:
        results["combined_diagnosis"] = {"status": "failed", "error": str(e)}
        print(f"❌ Combined diagnosis test failed: {str(e)}")
    
    # Lưu kết quả tests
    results["timestamp"] = str(Path(__file__).stat().st_mtime)
    
    with open("tests/results/diagnosis_test_result.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    
    # Kiểm tra kết quả tổng thể
    if all(test["status"] == "passed" for test in results.values() if isinstance(test, dict)):
        print("✅ All diagnosis tests passed!")
    else:
        print("⚠️ Some diagnosis tests failed. Check the results for details.") 