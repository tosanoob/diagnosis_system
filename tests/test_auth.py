import requests
import json
import os
import uuid
from pathlib import Path

# Cấu hình API endpoint
BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8100/api")

def test_login_logout():
    """
    Test các endpoint đăng nhập và đăng xuất
    
    Lưu ý: Test này giả định rằng hệ thống có sẵn một tài khoản với
    username='admin' và password='admin'
    
    Nếu tài khoản này không tồn tại, hãy tạo nó trước khi chạy test,
    hoặc thay đổi thông tin đăng nhập để phù hợp với tài khoản có sẵn
    """
    # Đăng nhập với tài khoản admin
    login_data = {
        "username": "admin",
        "password": "admin"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    
    # Kiểm tra status code
    assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}: {response.text}"
    
    # Kiểm tra cấu trúc response
    login_result = response.json()
    assert "access_token" in login_result, "Response should contain access_token"
    assert "token_type" in login_result, "Response should contain token_type"
    assert "expires_at" in login_result, "Response should contain expires_at"
    assert "user_id" in login_result, "Response should contain user_id"
    assert "username" in login_result, "Response should contain username"
    assert login_result["username"] == login_data["username"], "Username in response should match request"
    
    print(f"✅ Login test passed for user: {login_result['username']}")
    
    # Lưu token để đăng xuất và sử dụng cho các test khác
    token = login_result["access_token"]
    
    # Test đăng xuất
    logout_data = {
        "token": token
    }
    
    logout_response = requests.post(f"{BASE_URL}/auth/logout", json=logout_data)
    
    # Kiểm tra status code
    assert logout_response.status_code == 200, f"Expected status code 200 but got {logout_response.status_code}: {logout_response.text}"
    
    # Kiểm tra cấu trúc response
    logout_result = logout_response.json()
    assert "success" in logout_result, "Response should contain success field"
    assert logout_result["success"] is True, "Logout should be successful"
    
    print("✅ Logout test passed")
    
    # Cố gắng sử dụng token đã đăng xuất để truy cập API
    headers = {"Authorization": f"Bearer {token}"}

    # Test domain post
    test_domain = {
        "domain": f"Test Domain without token",
        "description": "Domain created during auth test"
    }
    update_response = requests.post(f"{BASE_URL}/domains", headers=headers, json=test_domain)
    assert update_response.status_code == 401, f"Expected status code 401 but got {update_response.status_code}"
    
    print("✅ Token revocation test passed")
    
    return True

def test_domain_auth():
    """
    Test xác thực cho các endpoint domain
    """
    # Đăng nhập để lấy token
    login_data = {
        "username": "admin",
        "password": "admin"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    
    # Xác minh đăng nhập thành công
    if response.status_code != 200:
        print(f"⚠️ Không thể đăng nhập: {response.status_code} - {response.text}")
        return False
        
    login_result = response.json()
    token = login_result["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Kiểm tra truy cập các endpoint đọc không có token
    read_response = requests.get(f"{BASE_URL}/domains")
    assert read_response.status_code == 200, "Read endpoints should be accessible without token"
    
    # Kiểm tra tạo domain với token
    test_domain = {
        "domain": f"Test Auth Domain {uuid.uuid4().hex[:8]}",
        "description": "Domain created during auth test"
    }
    
    create_response = requests.post(f"{BASE_URL}/domains", json=test_domain, headers=headers)
    
    # Xác minh tạo thành công và có trường created_by
    assert create_response.status_code == 200, f"Create with token should succeed: {create_response.status_code} - {create_response.text}"
    created_domain = create_response.json()
    assert "created_by" in created_domain, "Response should include created_by field"
    assert created_domain["created_by"] == login_result["user_id"], "created_by should match the current user ID"
    
    domain_id = created_domain["id"]
    print(f"✅ Create domain with auth test passed for domain ID: {domain_id}")
    
    # Kiểm tra cập nhật domain với token
    update_data = {
        "description": f"Domain updated during auth test at {uuid.uuid4().hex[:8]}"
    }
    
    update_response = requests.put(f"{BASE_URL}/domains/{domain_id}", json=update_data, headers=headers)
    
    # Xác minh cập nhật thành công và có trường updated_by
    assert update_response.status_code == 200, f"Update with token should succeed: {update_response.status_code} - {update_response.text}"
    updated_domain = update_response.json()
    assert "updated_by" in updated_domain, "Response should include updated_by field"
    assert updated_domain["updated_by"] == login_result["user_id"], "updated_by should match the current user ID"
    
    print(f"✅ Update domain with auth test passed for domain ID: {domain_id}")
    
    # Đăng xuất để thu hồi token
    logout_data = {"token": token}
    logout_response = requests.post(f"{BASE_URL}/auth/logout", json=logout_data)
    assert logout_response.status_code == 200, "Logout should succeed"
    
    # Cố gắng cập nhật với token đã thu hồi
    update_data = {
        "description": "This update should fail due to revoked token"
    }
    
    invalid_update = requests.put(f"{BASE_URL}/domains/{domain_id}", json=update_data, headers=headers)
    assert invalid_update.status_code == 401, f"Update with revoked token should fail: {invalid_update.status_code}"
    
    print("✅ Authentication validation test passed")
    
    # Đăng nhập lại để xóa domain đã tạo
    new_response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    new_token = new_response.json()["access_token"]
    new_headers = {"Authorization": f"Bearer {new_token}"}
    
    # Xóa domain đã tạo
    delete_response = requests.delete(f"{BASE_URL}/domains/{domain_id}", headers=new_headers)
    assert delete_response.status_code == 200, f"Delete with token should succeed: {delete_response.status_code} - {delete_response.text}"
    deleted_domain = delete_response.json()
    assert "deleted_by" in deleted_domain, "Response should include deleted_by field"
    assert deleted_domain["deleted_by"] == login_result["user_id"], "deleted_by should match the current user ID"
    
    print(f"✅ Delete domain with auth test passed for domain ID: {domain_id}")
    
    return True

def test_disease_auth():
    """
    Test xác thực cho các endpoint disease
    """
    # Đăng nhập để lấy token
    login_data = {
        "username": "admin",
        "password": "admin"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    
    # Xác minh đăng nhập thành công
    if response.status_code != 200:
        print(f"⚠️ Không thể đăng nhập: {response.status_code} - {response.text}")
        return False
        
    login_result = response.json()
    token = login_result["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Kiểm tra truy cập các endpoint đọc không có token
    read_response = requests.get(f"{BASE_URL}/diseases")
    assert read_response.status_code == 200, "Read endpoints should be accessible without token"
    
    # Tạo disease với token
    test_disease = {
        "label": f"Test Auth Disease {uuid.uuid4().hex[:8]}",
        "description": "Disease created during auth test",
        "included_in_diagnosis": True
    }
    
    create_response = requests.post(f"{BASE_URL}/diseases", json=test_disease, headers=headers)
    
    # Xác minh tạo thành công
    assert create_response.status_code == 200, f"Create with token should succeed: {create_response.status_code} - {create_response.text}"
    created_disease = create_response.json()
    
    disease_id = created_disease.get("id")
    print(f"✅ Create disease with auth test passed for disease ID: {disease_id}")
    
    # Kiểm tra cập nhật disease với token
    update_data = {
        "description": f"Disease updated during auth test at {uuid.uuid4().hex[:8]}"
    }
    
    update_response = requests.put(f"{BASE_URL}/diseases/{disease_id}", json=update_data, headers=headers)
    
    # Xác minh cập nhật thành công
    assert update_response.status_code == 200, f"Update with token should succeed: {update_response.status_code} - {update_response.text}"
    
    print(f"✅ Update disease with auth test passed for disease ID: {disease_id}")
    
    # Xóa disease với token
    delete_response = requests.delete(f"{BASE_URL}/diseases/{disease_id}", headers=headers)
    
    # Xác minh xóa thành công
    assert delete_response.status_code == 200, f"Delete with token should succeed: {delete_response.status_code} - {delete_response.text}"
    
    print(f"✅ Delete disease with auth test passed for disease ID: {disease_id}")
    
    return True

def test_clinic_article_auth():
    """
    Test xác thực cho các endpoint clinic và article
    """
    # Đăng nhập để lấy token
    login_data = {
        "username": "admin",
        "password": "admin"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    
    # Xác minh đăng nhập thành công
    if response.status_code != 200:
        print(f"⚠️ Không thể đăng nhập: {response.status_code} - {response.text}")
        return False
        
    login_result = response.json()
    token = login_result["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test clinic - đọc không cần token
    read_response = requests.get(f"{BASE_URL}/clinic")
    assert read_response.status_code == 200, "Clinic read endpoints should be accessible without token"
    
    # Test clinic - tạo cần token
    test_clinic = {
        "name": f"Test Auth Clinic {uuid.uuid4().hex[:8]}",
        "description": "Clinic created during auth test",
        "location": "Test Location"
    }
    
    # Thử tạo clinic không có token
    no_auth_response = requests.post(f"{BASE_URL}/clinic", json=test_clinic)
    assert no_auth_response.status_code in [401, 403], f"Create without token should fail: {no_auth_response.status_code}"
    
    # Tạo clinic với token
    create_response = requests.post(f"{BASE_URL}/clinic", json=test_clinic, headers=headers)
    assert create_response.status_code == 200, f"Create with token should succeed: {create_response.status_code} - {create_response.text}"
    created_clinic = create_response.json()
    clinic_id = created_clinic.get("id")
    print(f"✅ Create clinic with auth test passed for clinic ID: {clinic_id}")
    
    # Test article - đọc không cần token
    read_response = requests.get(f"{BASE_URL}/article")
    assert read_response.status_code == 200, "Article read endpoints should be accessible without token"
    
    # Test article - tạo cần token
    test_article = {
        "title": f"Test Auth Article {uuid.uuid4().hex[:8]}",
        "summary": "Article created during auth test",
        "content": "This is test content for authentication testing"
    }
    
    # Thử tạo article không có token
    no_auth_response = requests.post(f"{BASE_URL}/article", json=test_article)
    assert no_auth_response.status_code in [401, 403], f"Create without token should fail: {no_auth_response.status_code}"
    
    # Tạo article với token
    create_response = requests.post(f"{BASE_URL}/article", json=test_article, headers=headers)
    assert create_response.status_code == 200, f"Create with token should succeed: {create_response.status_code} - {create_response.text}"
    created_article = create_response.json()
    article_id = created_article.get("id")
    print(f"✅ Create article with auth test passed for article ID: {article_id}")
    
    # Kiểm tra cập nhật và xóa với token
    # Xóa article
    delete_article_response = requests.delete(f"{BASE_URL}/article/{article_id}", headers=headers)
    assert delete_article_response.status_code == 200, f"Delete article with token should succeed"
    
    # Xóa clinic
    delete_clinic_response = requests.delete(f"{BASE_URL}/clinic/{clinic_id}", headers=headers)
    assert delete_clinic_response.status_code == 200, f"Delete clinic with token should succeed"
    
    print("✅ Delete operations with auth test passed")
    
    return True

if __name__ == "__main__":
    # Tạo thư mục để lưu kết quả
    Path("tests/results").mkdir(parents=True, exist_ok=True)
    
    # Chạy tests
    results = {}
    
    try:
        if test_login_logout():
            results["login_logout"] = {"status": "passed"}
        else:
            results["login_logout"] = {"status": "failed", "error": "Failed to complete login/logout test"}
    except Exception as e:
        results["login_logout"] = {"status": "failed", "error": str(e)}
        print(f"❌ Login/logout test failed: {str(e)}")
    
    try:
        if test_domain_auth():
            results["domain_auth"] = {"status": "passed"}
        else:
            results["domain_auth"] = {"status": "failed", "error": "Failed to complete domain auth test"}
    except Exception as e:
        results["domain_auth"] = {"status": "failed", "error": str(e)}
        print(f"❌ Domain auth test failed: {str(e)}")
    
    try:
        if test_disease_auth():
            results["disease_auth"] = {"status": "passed"}
        else:
            results["disease_auth"] = {"status": "failed", "error": "Failed to complete disease auth test"}
    except Exception as e:
        results["disease_auth"] = {"status": "failed", "error": str(e)}
        print(f"❌ Disease auth test failed: {str(e)}")
    
    try:
        if test_clinic_article_auth():
            results["clinic_article_auth"] = {"status": "passed"}
        else:
            results["clinic_article_auth"] = {"status": "failed", "error": "Failed to complete clinic/article auth test"}
    except Exception as e:
        results["clinic_article_auth"] = {"status": "failed", "error": str(e)}
        print(f"❌ Clinic/article auth test failed: {str(e)}")
    
    # Lưu kết quả tests
    results["timestamp"] = str(Path(__file__).stat().st_mtime)
    
    with open("tests/results/auth_test_result.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    
    # Kiểm tra kết quả tổng thể
    if all(test["status"] == "passed" for test in results.values() if isinstance(test, dict)):
        print("✅ All authentication tests passed!")
    else:
        print("⚠️ Some authentication tests failed. Check the results for details.") 