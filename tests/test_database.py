import requests
import json
import os
import uuid
from pathlib import Path

# Cấu hình API endpoint
BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8100/api")

def test_get_diseases():
    """
    Test endpoint lấy danh sách bệnh
    """
    # Gửi request
    response = requests.get(f"{BASE_URL}/db/diseases")
    
    # Kiểm tra status code
    assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}"
    
    # Kiểm tra cấu trúc response
    data = response.json()
    assert isinstance(data, list), "Response should be a list of diseases"
    
    # Nếu có dữ liệu, kiểm tra cấu trúc của phần tử đầu tiên
    if len(data) > 0:
        first_disease = data[0]
        assert "id" in first_disease, "Disease should have an id field"
        assert "name" in first_disease, "Disease should have a name field"
        assert "description" in first_disease, "Disease should have a description field"
    
    print(f"✅ Get diseases test passed, found {len(data)} diseases")

def test_get_domains():
    """
    Test endpoint lấy danh sách lĩnh vực y tế
    """
    # Gửi request
    response = requests.get(f"{BASE_URL}/db/domains")
    
    # Kiểm tra status code
    assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}"
    
    # Kiểm tra cấu trúc response
    data = response.json()
    assert isinstance(data, list), "Response should be a list of domains"
    
    # Nếu có dữ liệu, kiểm tra cấu trúc của phần tử đầu tiên
    if len(data) > 0:
        first_domain = data[0]
        assert "id" in first_domain, "Domain should have an id field"
        assert "name" in first_domain, "Domain should have a name field"
    
    print(f"✅ Get domains test passed, found {len(data)} domains")

def test_get_articles():
    """
    Test endpoint lấy danh sách bài viết
    """
    # Gửi request
    response = requests.get(f"{BASE_URL}/db/articles")
    
    # Kiểm tra status code
    assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}"
    
    # Kiểm tra cấu trúc response
    data = response.json()
    assert isinstance(data, list), "Response should be a list of articles"
    
    # Nếu có dữ liệu, kiểm tra cấu trúc của phần tử đầu tiên
    if len(data) > 0:
        first_article = data[0]
        assert "id" in first_article, "Article should have an id field"
        assert "title" in first_article, "Article should have a title field"
        assert "content" in first_article, "Article should have a content field"
    
    print(f"✅ Get articles test passed, found {len(data)} articles")

def test_search_diseases():
    """
    Test endpoint tìm kiếm bệnh
    """
    # Gửi request với từ khóa tìm kiếm
    response = requests.get(f"{BASE_URL}/db/diseases?search=da")
    
    # Kiểm tra status code
    assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}"
    
    # Kiểm tra cấu trúc response
    data = response.json()
    assert isinstance(data, list), "Response should be a list of diseases"
    
    print(f"✅ Search diseases test passed, found {len(data)} results")

def test_get_disease_by_id():
    """
    Test endpoint lấy thông tin chi tiết của một bệnh
    """
    # Trước tiên lấy danh sách bệnh để có ID mẫu
    response = requests.get(f"{BASE_URL}/db/diseases")
    assert response.status_code == 200, "Failed to get diseases list"
    
    diseases = response.json()
    if not diseases:
        print("⚠️ Skipping get disease by ID test due to lack of disease data")
        return
    
    # Lấy ID của bệnh đầu tiên
    disease_id = diseases[0]["id"]
    
    # Gửi request lấy chi tiết bệnh
    response = requests.get(f"{BASE_URL}/db/diseases/{disease_id}")
    
    # Kiểm tra status code
    assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}"
    
    # Kiểm tra cấu trúc response
    data = response.json()
    assert "id" in data, "Disease should have an id field"
    assert "name" in data, "Disease should have a name field"
    assert "description" in data, "Disease should have a description field"
    assert data["id"] == disease_id, f"Expected disease ID {disease_id} but got {data['id']}"
    
    print(f"✅ Get disease by ID test passed for disease ID: {disease_id}")

def test_get_roles():
    """
    Test endpoint lấy danh sách vai trò (roles)
    """
    # Gửi request
    response = requests.get(f"{BASE_URL}/db/roles")
    
    # Kiểm tra status code
    assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}"
    
    # Kiểm tra cấu trúc response
    data = response.json()
    assert isinstance(data, list), "Response should be a list of roles"
    
    print(f"✅ Get roles test passed, found {len(data)} roles")

def test_get_users():
    """
    Test endpoint lấy danh sách người dùng
    """
    # Gửi request
    response = requests.get(f"{BASE_URL}/db/users")
    
    # Kiểm tra status code
    assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}"
    
    # Kiểm tra cấu trúc response
    data = response.json()
    assert isinstance(data, list), "Response should be a list of users"
    
    # Nếu có dữ liệu, kiểm tra cấu trúc của phần tử đầu tiên
    if len(data) > 0:
        first_user = data[0]
        assert "id" in first_user, "User should have an id field"
        assert "username" in first_user, "User should have a username field"
        assert "email" in first_user, "User should have an email field"
        assert "role_id" in first_user, "User should have a role_id field"
    
    print(f"✅ Get users test passed, found {len(data)} users")

def test_create_and_update_disease():
    """
    Test endpoints tạo và cập nhật bệnh (CRUD operations)
    """
    # Dữ liệu mẫu để tạo bệnh mới
    test_disease = {
        "name": f"Test Disease {uuid.uuid4().hex[:8]}",
        "description": "This is a test disease created by automated testing",
        "symptoms": "Test symptoms",
        "causes": "Test causes",
        "treatments": "Test treatments",
        "preventions": "Test preventions",
        "domain_id": None  # Sẽ được cập nhật nếu có domains
    }
    
    # Lấy domain_id nếu có
    try:
        domains_response = requests.get(f"{BASE_URL}/db/domains")
        if domains_response.status_code == 200:
            domains = domains_response.json()
            if domains:
                test_disease["domain_id"] = domains[0]["id"]
    except Exception as e:
        print(f"Warning: Could not fetch domains: {str(e)}")
    
    try:
        # Gửi request tạo bệnh mới
        create_response = requests.post(f"{BASE_URL}/db/diseases", json=test_disease)
        
        # Kiểm tra status code
        assert create_response.status_code == 200, f"Expected status code 200 but got {create_response.status_code}"
        
        # Lấy dữ liệu bệnh vừa tạo
        created_disease = create_response.json()
        assert "id" in created_disease, "Created disease should have an id field"
        assert created_disease["name"] == test_disease["name"], "Created disease name should match input"
        
        # Lưu ID để sử dụng cho các test tiếp theo
        disease_id = created_disease["id"]
        
        print(f"✅ Create disease test passed, created disease with ID: {disease_id}")
        
        # Test cập nhật bệnh
        update_data = {
            "name": f"Updated {test_disease['name']}",
            "description": "Updated description by automated testing"
        }
        
        update_response = requests.put(f"{BASE_URL}/db/diseases/{disease_id}", json=update_data)
        
        # Kiểm tra status code
        assert update_response.status_code == 200, f"Expected status code 200 but got {update_response.status_code}"
        
        # Kiểm tra dữ liệu sau khi cập nhật
        updated_disease = update_response.json()
        assert updated_disease["name"] == update_data["name"], "Updated disease name should match input"
        assert updated_disease["description"] == update_data["description"], "Updated disease description should match input"
        
        print(f"✅ Update disease test passed for disease ID: {disease_id}")
        
        # Test xóa bệnh (soft delete)
        delete_response = requests.delete(f"{BASE_URL}/db/diseases/{disease_id}?soft_delete=true")
        
        # Kiểm tra status code
        assert delete_response.status_code == 200, f"Expected status code 200 but got {delete_response.status_code}"
        
        # Kiểm tra dữ liệu sau khi xóa
        deleted_disease = delete_response.json()
        assert deleted_disease["is_deleted"] == True, "Deleted disease should have is_deleted=True"
        
        print(f"✅ Delete disease test passed for disease ID: {disease_id}")
        
        return True
    except Exception as e:
        print(f"❌ Create/update/delete disease test failed: {str(e)}")
        return False

if __name__ == "__main__":
    # Tạo thư mục để lưu kết quả
    Path("tests/results").mkdir(parents=True, exist_ok=True)
    
    # Chạy tests
    results = {}
    
    try:
        test_get_diseases()
        results["get_diseases"] = {"status": "passed"}
    except Exception as e:
        results["get_diseases"] = {"status": "failed", "error": str(e)}
        print(f"❌ Get diseases test failed: {str(e)}")
    
    try:
        test_get_domains()
        results["get_domains"] = {"status": "passed"}
    except Exception as e:
        results["get_domains"] = {"status": "failed", "error": str(e)}
        print(f"❌ Get domains test failed: {str(e)}")
    
    try:
        test_get_articles()
        results["get_articles"] = {"status": "passed"}
    except Exception as e:
        results["get_articles"] = {"status": "failed", "error": str(e)}
        print(f"❌ Get articles test failed: {str(e)}")
    
    try:
        test_search_diseases()
        results["search_diseases"] = {"status": "passed"}
    except Exception as e:
        results["search_diseases"] = {"status": "failed", "error": str(e)}
        print(f"❌ Search diseases test failed: {str(e)}")
    
    try:
        test_get_disease_by_id()
        results["get_disease_by_id"] = {"status": "passed"}
    except Exception as e:
        results["get_disease_by_id"] = {"status": "failed", "error": str(e)}
        print(f"❌ Get disease by ID test failed: {str(e)}")
    
    try:
        test_get_roles()
        results["get_roles"] = {"status": "passed"}
    except Exception as e:
        results["get_roles"] = {"status": "failed", "error": str(e)}
        print(f"❌ Get roles test failed: {str(e)}")
    
    try:
        test_get_users()
        results["get_users"] = {"status": "passed"}
    except Exception as e:
        results["get_users"] = {"status": "failed", "error": str(e)}
        print(f"❌ Get users test failed: {str(e)}")
    
    try:
        if test_create_and_update_disease():
            results["create_update_disease"] = {"status": "passed"}
        else:
            results["create_update_disease"] = {"status": "failed", "error": "Failed to complete CRUD operations"}
    except Exception as e:
        results["create_update_disease"] = {"status": "failed", "error": str(e)}
        print(f"❌ Create/update disease test failed: {str(e)}")
    
    # Lưu kết quả tests
    results["timestamp"] = str(Path(__file__).stat().st_mtime)
    
    with open("tests/results/database_test_result.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    
    # Kiểm tra kết quả tổng thể
    if all(test["status"] == "passed" for test in results.values() if isinstance(test, dict)):
        print("✅ All database tests passed!")
    else:
        print("⚠️ Some database tests failed. Check the results for details.") 