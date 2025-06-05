#!/bin/bash

# Script setup và chạy diagnosis pipeline test
echo "🚀 Diagnosis Pipeline Test Setup & Run"
echo "======================================"

# Kiểm tra Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python3"
    exit 1
fi

# Kiểm tra pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 not found. Please install pip3"
    exit 1
fi

# Cài đặt dependencies
echo "📦 Installing required packages..."
pip3 install datasets google-genai numpy pillow tqdm

# Kiểm tra API key
if [ -z "$GEMINI_API_KEY" ]; then
    echo "⚠️  GEMINI_API_KEY not set. Using default key..."
    export GEMINI_API_KEY="GEMINI_API_KEY"
fi

# Tạo sample data nếu cần
echo "🔧 Creating sample data files..."
python3 create_sample_data.py

# Chạy test
echo "🧪 Running diagnosis pipeline test..."
python3 run_diagnosis_pipeline_test.py

echo "✅ Test completed!"
echo "📁 Check results in tests/results/ folder" 
