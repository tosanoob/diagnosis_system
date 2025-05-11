import requests
import json
import os
import uuid
from pathlib import Path
from datetime import datetime

# Cấu hình API endpoint
BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8100/api")

def test_get_domains():
    """
    Test endpoint lấy danh sách lĩnh vực y tế
    """
    # Gửi request
    response = requests.get(f"{BASE_URL}/domains")
    
    # Kiểm tra status code
    assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}"
    
    # Kiểm tra cấu trúc response
    data = response.json()
    assert isinstance(data, list), "Response should be a list of domains"
    
    # Nếu có dữ liệu, kiểm tra cấu trúc của phần tử đầu tiên
    if len(data) > 0:
        first_domain = data[0]
        assert "id" in first_domain, "Domain should have an id field"
        assert "domain" in first_domain, "Domain should have a domain field"
        
        # Kiểm tra các trường audit
        assert "created_at" in first_domain, "Domain should have a created_at field"
        assert "updated_at" in first_domain, "Domain should have an updated_at field"
    
    print(f"✅ Get domains test passed, found {len(data)} domains")

def test_get_domain_by_id():
    """
    Test endpoint lấy thông tin chi tiết của một lĩnh vực y tế
    """
    # Trước tiên lấy danh sách domain để có ID mẫu
    response = requests.get(f"{BASE_URL}/domains")
    assert response.status_code == 200, "Failed to get domains list"
    
    domains = response.json()
    if not domains:
        print("⚠️ Skipping get domain by ID test due to lack of domain data")
        return
    
    # Lấy ID của domain đầu tiên
    domain_id = domains[0]["id"]
    
    # Gửi request lấy chi tiết domain
    response = requests.get(f"{BASE_URL}/domains/{domain_id}")
    
    # Kiểm tra status code
    assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}"
    
    # Kiểm tra cấu trúc response
    data = response.json()
    assert "id" in data, "Domain should have an id field"
    assert "domain" in data, "Domain should have a domain field"
    assert data["id"] == domain_id, f"Expected domain ID {domain_id} but got {data['id']}"
    
    # Kiểm tra các trường audit
    assert "created_at" in data, "Domain should have a created_at field"
    assert "updated_at" in data, "Domain should have an updated_at field"
    assert "created_by" in data, "Domain should have a created_by field"
    
    print(f"✅ Get domain by ID test passed for domain ID: {domain_id}")

def test_create_and_update_domain():
    """
    Test endpoints tạo và cập nhật lĩnh vực y tế (CRUD operations)
    """
    # Dữ liệu mẫu để tạo domain mới
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    test_user = f"test_user_{uuid.uuid4().hex[:8]}"
    test_domain = {
        "domain": f"This is a test domain {now}",
        "description": f"This is a test domain created by automated testing at {now}",
        "created_by": test_user
    }
    
    try:
        # Gửi request tạo domain mới
        create_response = requests.post(f"{BASE_URL}/domains", json=test_domain)
        
        # Kiểm tra status code
        assert create_response.status_code == 200, f"Expected status code 200 but got {create_response.status_code}"
        
        # Lấy dữ liệu domain vừa tạo
        created_domain = create_response.json()
        assert "id" in created_domain, "Created domain should have an id field"
        assert created_domain["domain"] == test_domain["domain"], "Created domain domain should match input"
        
        # Kiểm tra các trường audit
        assert "created_at" in created_domain, "Domain should have a created_at field"
        assert "updated_at" in created_domain, "Domain should have an updated_at field"
        assert created_domain["created_by"] == test_user, "Created domain should have correct created_by field"
        
        # Lưu ID để sử dụng cho các test tiếp theo
        domain_id = created_domain["id"]
        
        print(f"✅ Create domain test passed, created domain with ID: {domain_id}")
        
        # Test cập nhật domain
        update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        updated_user = f"updated_user_{uuid.uuid4().hex[:8]}"
        update_data = {
            "domain": f"Updated {test_domain['domain']} at {update_time}",
            "description": f"Updated description by automated testing at {update_time}",
            "updated_by": updated_user
        }
        
        update_response = requests.put(f"{BASE_URL}/domains/{domain_id}", json=update_data)
        
        # Kiểm tra status code
        assert update_response.status_code == 200, f"Expected status code 200 but got {update_response.status_code}"
        
        # Kiểm tra dữ liệu sau khi cập nhật
        updated_domain = update_response.json()
        assert updated_domain["domain"] == update_data["domain"], "Updated domain domain should match input"
        assert updated_domain["description"] == update_data["description"], "Updated domain description should match input"
        assert updated_domain["updated_by"] == updated_user, "Updated domain should have correct updated_by field"
        
        print(f"✅ Update domain test passed for domain ID: {domain_id}")
        
        # Test xóa domain (soft delete) với người xóa
        deleted_user = f"deleted_user_{uuid.uuid4().hex[:8]}"
        delete_response = requests.delete(f"{BASE_URL}/domains/{domain_id}?soft_delete=true&deleted_by={deleted_user}")
        
        # Kiểm tra status code
        assert delete_response.status_code == 200, f"Expected status code 200 but got {delete_response.status_code}"
        
        # Kiểm tra dữ liệu sau khi xóa
        deleted_domain = delete_response.json()
        assert deleted_domain["id"] == domain_id, "Deleted domain should have the same id as the original domain"
        assert deleted_domain["deleted_by"] == deleted_user, "Deleted domain should have correct deleted_by field"
        assert deleted_domain["deleted_at"] is not None, "Deleted domain should have deleted_at set"
        
        print(f"✅ Delete domain test passed for domain ID: {domain_id}")
        
        return True
    except Exception as e:
        print(f"❌ Create/update/delete domain test failed: {str(e)}")
        return False

if __name__ == "__main__":
    # Tạo thư mục để lưu kết quả
    Path("tests/results").mkdir(parents=True, exist_ok=True)
    
    # Chạy tests
    results = {}
    
    try:
        test_get_domains()
        results["get_domains"] = {"status": "passed"}
    except Exception as e:
        results["get_domains"] = {"status": "failed", "error": str(e)}
        print(f"❌ Get domains test failed: {str(e)}")
    
    try:
        test_get_domain_by_id()
        results["get_domain_by_id"] = {"status": "passed"}
    except Exception as e:
        results["get_domain_by_id"] = {"status": "failed", "error": str(e)}
        print(f"❌ Get domain by ID test failed: {str(e)}")
    
    try:
        if test_create_and_update_domain():
            results["create_update_domain"] = {"status": "passed"}
        else:
            results["create_update_domain"] = {"status": "failed", "error": "Failed to complete CRUD operations"}
    except Exception as e:
        results["create_update_domain"] = {"status": "failed", "error": str(e)}
        print(f"❌ Create/update domain test failed: {str(e)}")
    
    # Lưu kết quả tests
    results["timestamp"] = str(Path(__file__).stat().st_mtime)
    
    with open("tests/results/domain_test_result.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    
    # Kiểm tra kết quả tổng thể
    if all(test["status"] == "passed" for test in results.values() if isinstance(test, dict)):
        print("✅ All domain tests passed!")
    else:
        print("⚠️ Some domain tests failed. Check the results for details.") 