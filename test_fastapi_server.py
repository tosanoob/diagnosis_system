"""Test script for FastAPI image encoding server."""

import requests
import base64
import json
from PIL import Image
import io
import numpy as np

def create_test_image() -> str:
    """Create a test image and convert to base64."""
    # Create a simple test image
    image = Image.new('RGB', (224, 224), color='red')
    
    # Convert to base64
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG')
    image_bytes = buffer.getvalue()
    base64_string = base64.b64encode(image_bytes).decode('utf-8')
    
    return base64_string

def test_health_endpoint(base_url: str = "http://localhost:8000"):
    """Test health check endpoint."""
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Health check status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

def test_encode_endpoint(base_url: str = "http://localhost:8000"):
    """Test encode endpoint."""
    try:
        # Create test images
        test_image1 = create_test_image()
        test_image2 = create_test_image()
        
        # Prepare request
        request_data = {
            "images": [test_image1, test_image2],
            "texts": ["test text 1", "test text 2"]  # Not used but required by schema
        }
        
        # Send request
        response = requests.post(
            f"{base_url}/encode",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Encode request status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            embeddings = result["image_embeddings"]
            
            print(f"Number of embeddings: {len(embeddings)}")
            if embeddings:
                print(f"Embedding dimension: {len(embeddings[0])}")
                print(f"First few values of first embedding: {embeddings[0][:5]}")
            
            return True
        else:
            print(f"Error response: {response.text}")
            return False
            
    except Exception as e:
        print(f"Encode test failed: {e}")
        return False

def test_encode_with_file_image(image_path: str, base_url: str = "http://localhost:8000"):
    """Test encode endpoint with a real image file."""
    try:
        # Load and encode image
        with open(image_path, "rb") as image_file:
            image_bytes = image_file.read()
            base64_string = base64.b64encode(image_bytes).decode('utf-8')
        
        # Prepare request
        request_data = {
            "images": [base64_string],
            "texts": ["real image test"]
        }
        
        # Send request
        response = requests.post(
            f"{base_url}/encode",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Real image encode status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            embeddings = result["image_embeddings"]
            
            print(f"Number of embeddings: {len(embeddings)}")
            if embeddings:
                print(f"Embedding dimension: {len(embeddings[0])}")
                
            return True
        else:
            print(f"Error response: {response.text}")
            return False
            
    except FileNotFoundError:
        print(f"Image file not found: {image_path}")
        return False
    except Exception as e:
        print(f"Real image test failed: {e}")
        return False

if __name__ == "__main__":
    base_url = "http://localhost:8000"
    
    print("=== Testing FastAPI Image Encoding Server ===")
    
    # Test health endpoint
    print("\n1. Testing health endpoint...")
    health_ok = test_health_endpoint(base_url)
    
    if health_ok:
        # Test encode endpoint with synthetic images
        print("\n2. Testing encode endpoint with synthetic images...")
        encode_ok = test_encode_endpoint(base_url)
        
        # Optionally test with a real image (uncomment and provide path)
        # print("\n3. Testing encode endpoint with real image...")
        # test_encode_with_file_image("/path/to/your/image.jpg", base_url)
    else:
        print("Server not healthy, skipping encode tests")
    
    print("\n=== Test completed ===") 