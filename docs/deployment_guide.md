# Hướng dẫn Deployment với Gunicorn/Uvicorn và Ngrok

## Tổng quan

Ứng dụng FastAPI hiện tại đã được tối ưu để chạy với multiple workers mà không có conflicts. Ngrok được quản lý độc lập bên ngoài application để đảm bảo tính ổn định và khả năng mở rộng.

## Architecture

```
Internet → Ngrok Tunnel → Load Balancer → FastAPI Workers
                           (External)     (Gunicorn/Uvicorn)
```

## Các phương thức triển khai

### 1. Sử dụng Script tự động (Recommended)

Script `scripts/run_with_ngrok.sh` cung cấp giải pháp all-in-one:

```bash
# Chạy với Gunicorn + 4 workers + Ngrok
./scripts/run_with_ngrok.sh --workers 4 --server gunicorn

# Chạy với Uvicorn + custom domain
./scripts/run_with_ngrok.sh --server uvicorn --domain myapp.ngrok.io --token YOUR_TOKEN

# Chạy chỉ app server, không có ngrok
./scripts/run_with_ngrok.sh --no-ngrok --workers 8

# Custom port và host
./scripts/run_with_ngrok.sh --host 127.0.0.1 --port 9000 --workers 2
```

### 2. Manual Setup

#### Option A: Gunicorn (Production)

```bash
# Terminal 1: Start Gunicorn with multiple workers
gunicorn app.main:app \
    --bind 0.0.0.0:8123 \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    --log-level info

# Terminal 2: Start Ngrok tunnel
ngrok http 8123
```

#### Option B: Uvicorn (Development)

```bash
# Terminal 1: Start Uvicorn with multiple workers
uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8123 \
    --workers 4 \
    --log-level info

# Terminal 2: Start Ngrok tunnel
ngrok http 8123 --domain your-custom-domain.ngrok.io
```

#### Option C: Uvicorn Single Worker (Simple)

```bash
# Terminal 1: Start single worker
python app/main.py --host 0.0.0.0 --port 8123 --workers 1

# Terminal 2: Start Ngrok
ngrok http 8123
```

## Configuration

### Environment Variables

```bash
# .env file
HOST=0.0.0.0
PORT=8123
WORKERS=4
DEBUG=false
LOG_LEVEL=info

# Database
SQLITE_DB_PATH=runtime/db.sqlite3

# APIs
GEMINI_API_KEY=your_gemini_key
EMBEDDING_URL=your_embedding_url
EMBEDDING_API_KEY=your_embedding_key
```

### Ngrok Configuration

```bash
# Set auth token (one time)
ngrok authtoken YOUR_AUTH_TOKEN

# Create ngrok.yml config file
echo "
version: \"2\"
authtoken: YOUR_AUTH_TOKEN
tunnels:
  fastapi:
    proto: http
    addr: 8123
    domain: your-custom-domain.ngrok.io
" > ~/.ngrok2/ngrok.yml

# Start with config
ngrok start fastapi
```

## Performance Tuning

### Gunicorn Optimizations

```bash
gunicorn app.main:app \
    --bind 0.0.0.0:8123 \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --worker-connections 1000 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --timeout 30 \
    --keep-alive 5 \
    --preload \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log
```

### Uvicorn Optimizations

```bash
uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8123 \
    --workers 4 \
    --loop uvloop \
    --http httptools \
    --log-level info \
    --access-log
```

### System Optimizations

```bash
# Increase file descriptors
ulimit -n 65536

# Tune TCP settings
echo 'net.core.somaxconn = 1024' >> /etc/sysctl.conf
echo 'net.ipv4.tcp_max_syn_backlog = 1024' >> /etc/sysctl.conf
sysctl -p
```

## Monitoring và Health Checks

### Health Check Endpoints

Application cung cấp các endpoints để monitoring:

```bash
# Basic health check
curl http://localhost:8123/docs

# API health
curl http://localhost:8123/api/health

# Through ngrok
curl https://your-tunnel.ngrok.app/docs
```

### Process Monitoring

```bash
# Check Gunicorn processes
ps aux | grep gunicorn

# Check Uvicorn processes  
ps aux | grep uvicorn

# Check Ngrok process
ps aux | grep ngrok

# Check port usage
lsof -i :8123
```

### Log Monitoring

```bash
# Application logs
tail -f logs/app.log

# Access logs (Gunicorn)
tail -f logs/access.log

# Error logs (Gunicorn)
tail -f logs/error.log

# Ngrok logs
tail -f logs/ngrok.log
```

## Load Testing

### Test Local Application

```bash
# Install tools
pip install locust httpx

# Basic load test
ab -n 1000 -c 10 http://localhost:8123/docs

# Advanced load test with Locust
locust -f tests/load_test.py --host http://localhost:8123
```

### Test Ngrok Tunnel

```bash
# Test ngrok endpoint
ab -n 100 -c 5 https://your-tunnel.ngrok.app/docs

# Monitor ngrok dashboard
open http://localhost:4040
```

## Troubleshooting

### Common Issues

1. **Port already in use**:
   ```bash
   lsof -ti:8123 | xargs kill -9
   ```

2. **Too many workers**:
   ```bash
   # Reduce workers if system resources are limited
   --workers 2
   ```

3. **Ngrok connection issues**:
   ```bash
   # Check ngrok status
   curl http://localhost:4040/api/tunnels
   
   # Restart ngrok
   pkill ngrok
   ngrok http 8123
   ```

4. **Memory issues**:
   ```bash
   # Monitor memory usage
   htop
   
   # Reduce workers or use --preload
   gunicorn app.main:app --workers 2 --preload
   ```

### Performance Issues

1. **High CPU usage**:
   - Reduce number of workers
   - Check for infinite loops in code
   - Profile with `py-spy`

2. **High memory usage**:
   - Use `--max-requests` to restart workers periodically
   - Enable `--preload` for shared memory
   - Monitor with `memory_profiler`

3. **Slow response times**:
   - Check database connection pooling
   - Monitor slow queries
   - Use async/await properly

## Production Deployment

### Using systemd (Linux)

```bash
# Create service file
sudo tee /etc/systemd/system/fastapi.service << EOF
[Unit]
Description=FastAPI Application
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/path/to/your/app
Environment=PATH=/path/to/your/venv/bin
ExecStart=/path/to/your/venv/bin/gunicorn app.main:app --bind 0.0.0.0:8123 --workers 4 --worker-class uvicorn.workers.UvicornWorker
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl enable fastapi
sudo systemctl start fastapi
sudo systemctl status fastapi
```

### Using Docker

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8123

CMD ["gunicorn", "app.main:app", "--bind", "0.0.0.0:8123", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker"]
```

```bash
# Build and run
docker build -t fastapi-app .
docker run -p 8123:8123 -d fastapi-app

# With ngrok in separate container
docker run -d --net=host ngrok/ngrok:latest http 8123
```

### Using Nginx Reverse Proxy

```nginx
upstream fastapi {
    server 127.0.0.1:8123;
}

server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://fastapi;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## Best Practices

1. **Development**: Sử dụng script `run_with_ngrok.sh` với uvicorn
2. **Staging**: Sử dụng Gunicorn với ít workers để test
3. **Production**: Sử dụng Gunicorn + Nginx + systemd, không dùng ngrok
4. **Load testing**: Test thoroughly trước khi deploy production
5. **Monitoring**: Setup proper logging và monitoring
6. **Security**: Không expose ngrok tunnels trong production

## Security Considerations

- Ngrok chỉ nên dùng cho development/testing
- Production nên dùng proper SSL/TLS với reverse proxy
- Implement rate limiting
- Use authentication cho sensitive endpoints
- Monitor và log tất cả requests
``` 