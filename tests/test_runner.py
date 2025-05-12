import os
import sys
import json
import time
import importlib
from pathlib import Path
import argparse
import subprocess

def run_test_file(test_file_path, api_base_url=None):
    """
    Chạy một file test cụ thể bằng cách import và thực thi
    """
    print(f"\n{'='*60}")
    print(f"Running tests in {test_file_path}...")
    print(f"{'='*60}")

    if api_base_url:
        os.environ["API_BASE_URL"] = api_base_url
        print(f"Using API endpoint: {api_base_url}")
    else:
        # Mặc định là localhost:8100/api
        os.environ["API_BASE_URL"] = "http://localhost:8100/api"
        print(f"Using default API endpoint: {os.environ['API_BASE_URL']}")
    # Chạy file test như một subprocess
    result = subprocess.run([sys.executable, test_file_path], capture_output=True, text=True)
    
    # In output
    if result.stdout:
        print(result.stdout)
    
    # In lỗi nếu có
    if result.stderr:
        print("ERRORS:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
    
    return result.returncode == 0

def run_all_tests(api_base_url=None):
    """
    Chạy tất cả các file test trong thư mục tests
    """
    # Thiết lập biến môi trường cho API endpoint nếu được cung cấp
    if api_base_url:
        os.environ["API_BASE_URL"] = api_base_url
        print(f"Using API endpoint: {api_base_url}")
    else:
        # Mặc định là localhost:8100/api
        os.environ["API_BASE_URL"] = "http://localhost:8100/api"
        print(f"Using default API endpoint: {os.environ['API_BASE_URL']}")
    
    # Tạo thư mục results nếu chưa có
    results_dir = Path("tests/results")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Tìm tất cả các file test
    test_dir = Path("tests")
    test_files = sorted([f for f in test_dir.glob("test_*.py") if f.name != "test_runner.py"])
    
    if not test_files:
        print("No test files found in tests directory.")
        return False
    
    # Chạy từng file test và thu thập kết quả
    print(f"Found {len(test_files)} test files to run:")
    for f in test_files:
        print(f"  - {f.name}")
    
    print("\nStarting test execution...")
    
    # Thông tin về test run
    test_run = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "api_endpoint": os.environ["API_BASE_URL"],
        "tests": {},
        "summary": {
            "total": len(test_files),
            "passed": 0,
            "failed": 0
        }
    }
    
    # Chạy từng test file
    for test_file in test_files:
        test_name = test_file.stem
        success = run_test_file(test_file)
        
        # Cập nhật kết quả
        if success:
            test_run["tests"][test_name] = "passed"
            test_run["summary"]["passed"] += 1
        else:
            test_run["tests"][test_name] = "failed"
            test_run["summary"]["failed"] += 1
    
    # In tổng kết
    print(f"\n{'='*60}")
    print(f"TEST RUN SUMMARY")
    print(f"{'='*60}")
    print(f"Total test files: {test_run['summary']['total']}")
    print(f"Passed: {test_run['summary']['passed']}")
    print(f"Failed: {test_run['summary']['failed']}")
    
    # Lưu kết quả
    with open(results_dir / "test_run_summary.json", "w", encoding="utf-8") as f:
        json.dump(test_run, f, indent=2)
    
    return test_run["summary"]["failed"] == 0

if __name__ == "__main__":
    # Cấu hình command line arguments
    parser = argparse.ArgumentParser(description="Run API tests")
    parser.add_argument("--api-url", type=str, help="Base URL for API (e.g., http://localhost:8100/api)")
    parser.add_argument("--test-file", type=str, help="Run a specific test file only")
    
    args = parser.parse_args()
    
    if args.test_file:
        # Chạy file test cụ thể
        test_file_path = Path("tests") / args.test_file
        if not test_file_path.exists():
            test_file_path = Path(args.test_file)
            if not test_file_path.exists():
                print(f"Test file not found: {args.test_file}")
                sys.exit(1)
        
        success = run_test_file(test_file_path, args.api_url)
        sys.exit(0 if success else 1)
    else:
        # Chạy tất cả tests
        success = run_all_tests(args.api_url)
        sys.exit(0 if success else 1) 