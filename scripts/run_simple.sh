#!/bin/bash

# Simple script to run FastAPI with basic Python
# Usage: ./scripts/run_simple.sh [port] [workers]

PORT=${1:-8123}
WORKERS=${2:-4}

echo "🚀 Starting FastAPI with Python..."
echo "Port: $PORT, Workers: $WORKERS"

# Test import first
echo "Testing app import..."
if ! python -c "from app.main import app; print('✅ Import successful')"; then
    echo "❌ Cannot import app. Check your dependencies."
    exit 1
fi

# Create logs directory
mkdir -p logs

# Start the app
echo "Starting server..."
python app/main.py --host 0.0.0.0 --port $PORT --workers $WORKERS 