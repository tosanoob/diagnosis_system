#!/bin/bash

# Script chạy FastAPI với Ngrok tunnel external
# Usage: ./scripts/run_with_ngrok.sh [options]

set -e

# Default values
HOST="0.0.0.0"
PORT=8123
WORKERS=4
SERVER_TYPE="uvicorn"  # uvicorn or python
NGROK_DOMAIN=""
NGROK_AUTHTOKEN=""
LOG_LEVEL="info"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --host HOST           Host to bind (default: $HOST)"
    echo "  -p, --port PORT           Port to bind (default: $PORT)"
    echo "  -w, --workers WORKERS     Number of workers (default: $WORKERS)"
    echo "  -s, --server SERVER       Server type: uvicorn|python (default: $SERVER_TYPE)"
    echo "  -d, --domain DOMAIN       Ngrok custom domain"
    echo "  -t, --token TOKEN         Ngrok auth token"
    echo "  -l, --log-level LEVEL     Log level (default: $LOG_LEVEL)"
    echo "  --no-ngrok               Don't start ngrok tunnel"
    echo "  --help                   Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 --workers 4 --port 8123"
    echo "  $0 --server uvicorn --workers 1 --domain myapp.ngrok.io"
    echo "  $0 --no-ngrok --workers 8"
    echo ""
    echo "Environment files:"
    echo "  .env.ngrok               Contains NGROK_DOMAIN and NGROK_AUTHTOKEN"
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to load environment from .env.ngrok
load_ngrok_env() {
    local env_file=".env.ngrok"
    
    if [[ -f "$env_file" ]]; then
        log_info "Loading ngrok configuration from $env_file"
        
        # Read file and set variables
        while IFS= read -r line || [ -n "$line" ]; do
            # Skip comments and empty lines
            [[ "$line" =~ ^[[:space:]]*# ]] && continue
            [[ -z "${line// }" ]] && continue
            
            # Extract key=value pairs
            if [[ "$line" =~ ^[[:space:]]*([^=]+)=(.*)$ ]]; then
                local key="${BASH_REMATCH[1]// /}"
                local value="${BASH_REMATCH[2]}"
                
                # Remove quotes if present
                value="${value%\"}"
                value="${value#\"}"
                value="${value%\'}"
                value="${value#\'}"
                
                case "$key" in
                    NGROK_DOMAIN)
                        if [[ -z "$NGROK_DOMAIN" ]]; then
                            NGROK_DOMAIN="$value"
                            log_info "  NGROK_DOMAIN: $NGROK_DOMAIN"
                        fi
                        ;;
                    NGROK_AUTHTOKEN)
                        if [[ -z "$NGROK_AUTHTOKEN" ]]; then
                            NGROK_AUTHTOKEN="$value"
                            log_info "  NGROK_AUTHTOKEN: Set (hidden)"
                        fi
                        ;;
                esac
            fi
        done < "$env_file"
    else
        log_info "No .env.ngrok file found (optional)"
    fi
}

# Parse command line arguments
ENABLE_NGROK=true

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--host)
            HOST="$2"
            shift 2
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -w|--workers)
            WORKERS="$2"
            shift 2
            ;;
        -s|--server)
            SERVER_TYPE="$2"
            shift 2
            ;;
        -d|--domain)
            NGROK_DOMAIN="$2"
            shift 2
            ;;
        -t|--token)
            NGROK_AUTHTOKEN="$2"
            shift 2
            ;;
        -l|--log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --no-ngrok)
            ENABLE_NGROK=false
            shift
            ;;
        --help)
            print_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Load ngrok environment after parsing arguments (so CLI args take precedence)
load_ngrok_env

# Validate server type
if [[ "$SERVER_TYPE" != "uvicorn" && "$SERVER_TYPE" != "python" ]]; then
    log_error "Invalid server type: $SERVER_TYPE. Must be 'uvicorn' or 'python'"
    exit 1
fi

# Check if port is available
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    log_error "Port $PORT is already in use"
    exit 1
fi

# Create necessary directories
mkdir -p logs runtime

# Test if app can be imported
log_info "Testing application import..."
if ! python -c "from app.main import app; print('✅ App import successful')" 2>/dev/null; then
    log_error "❌ Cannot import app.main:app"
    log_error "Make sure you're in the correct directory and dependencies are installed"
    exit 1
fi

log_info "Starting FastAPI application..."
log_info "Server: $SERVER_TYPE, Host: $HOST, Port: $PORT, Workers: $WORKERS"

# Function to cleanup processes on exit
cleanup() {
    log_info "Cleaning up processes..."
    
    # Kill app server
    if [[ -n $APP_PID ]]; then
        kill $APP_PID 2>/dev/null || true
        wait $APP_PID 2>/dev/null || true
        log_info "App server stopped"
    fi
    
    # Kill ngrok
    if [[ -n $NGROK_PID ]]; then
        kill $NGROK_PID 2>/dev/null || true
        wait $NGROK_PID 2>/dev/null || true
        log_info "Ngrok tunnel stopped"
    fi
    
    exit 0
}

# Set trap for cleanup
trap cleanup SIGINT SIGTERM EXIT

# Start the application server
if [[ "$SERVER_TYPE" == "uvicorn" ]]; then
    # Using Uvicorn
    log_info "Starting Uvicorn server..."
    if [[ $WORKERS -gt 1 ]]; then
        uvicorn app.main:app \
            --host $HOST \
            --port $PORT \
            --workers $WORKERS \
            --log-level $LOG_LEVEL &
    else
        uvicorn app.main:app \
            --host $HOST \
            --port $PORT \
            --log-level $LOG_LEVEL &
    fi
    
    APP_PID=$!
    log_info "Uvicorn started with PID: $APP_PID"
    
elif [[ "$SERVER_TYPE" == "python" ]]; then
    # Using Python directly
    log_info "Starting Python server..."
    python app/main.py \
        --host $HOST \
        --port $PORT \
        --workers $WORKERS \
        --log-file logs/app.log &
    
    APP_PID=$!
    log_info "Python server started with PID: $APP_PID"
fi

# Wait for app to start
sleep 5

# Check if app is running
if ! kill -0 $APP_PID 2>/dev/null; then
    log_error "Failed to start application server"
    exit 1
fi

# Test if app is responding
if curl -s http://localhost:$PORT/docs >/dev/null 2>&1; then
    log_info "✅ Application is responding at http://localhost:$PORT"
else
    log_warn "⚠️  Application may not be ready yet"
fi

# Start ngrok tunnel if enabled
if [[ "$ENABLE_NGROK" == true ]]; then
    # Check if ngrok is installed
    if ! command -v ngrok &> /dev/null; then
        log_error "Ngrok is not installed. Please install it from: https://ngrok.com/download"
        exit 1
    fi
    
    # Set auth token if provided
    if [[ -n "$NGROK_AUTHTOKEN" ]]; then
        ngrok authtoken "$NGROK_AUTHTOKEN"
        log_info "Ngrok auth token set"
    fi
    
    # Start ngrok tunnel
    NGROK_CMD="ngrok http $PORT --log stdout"
    
    if [[ -n "$NGROK_DOMAIN" ]]; then
        NGROK_CMD="$NGROK_CMD --domain=$NGROK_DOMAIN"
    fi
    
    log_info "Starting ngrok tunnel..."
    $NGROK_CMD > logs/ngrok.log 2>&1 &
    NGROK_PID=$!
    
    # Wait for ngrok to start and get URL
    sleep 3
    
    # Extract ngrok URL from log or API
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for tunnel in data['tunnels']:
        if tunnel['proto'] == 'https':
            print(tunnel['public_url'])
            break
except:
    pass
" 2>/dev/null)
    
    if [[ -n "$NGROK_URL" ]]; then
        log_info "🌐 Ngrok tunnel established:"
        log_info "   Public URL: $NGROK_URL"
        log_info "   Local URL:  http://localhost:$PORT"
        log_info "   Dashboard:  http://localhost:4040"
    else
        log_warn "⚠️  Could not retrieve ngrok URL. Check logs/ngrok.log"
    fi
else
    log_info "Ngrok tunnel disabled"
fi

# Health check
log_info "Performing health check..."
if curl -s http://localhost:$PORT/docs >/dev/null 2>&1; then
    log_info "✅ Health check passed"
else
    log_error "❌ Health check failed"
fi

# Show status
echo ""
log_info "🚀 Application is running!"
log_info "   Local API:     http://localhost:$PORT"
log_info "   API Docs:      http://localhost:$PORT/docs"
log_info "   Server Type:   $SERVER_TYPE ($WORKERS workers)"

if [[ "$ENABLE_NGROK" == true && -n "$NGROK_URL" ]]; then
    log_info "   Public API:    $NGROK_URL"
    log_info "   Public Docs:   $NGROK_URL/docs"
fi

echo ""
log_info "Press Ctrl+C to stop all services"

# Keep script running and monitor processes
while true; do
    sleep 5
    
    # Check if app process is still running
    if ! kill -0 $APP_PID 2>/dev/null; then
        log_error "Application process died unexpectedly"
        exit 1
    fi
    
    # Check if ngrok process is still running (if enabled)
    if [[ "$ENABLE_NGROK" == true && -n "$NGROK_PID" ]]; then
        if ! kill -0 $NGROK_PID 2>/dev/null; then
            log_warn "Ngrok process died, restarting..."
            $NGROK_CMD > logs/ngrok.log 2>&1 &
            NGROK_PID=$!
        fi
    fi
done 