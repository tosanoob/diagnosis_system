FROM python:3.11-slim

WORKDIR /app

# Cài đặt các gói phụ thuộc cần thiết
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ mã nguồn vào container
COPY app/ /app/app/
COPY runtime/ /app/runtime/
COPY scripts/ /app/scripts/

# Đảm bảo thư mục dữ liệu tồn tại
RUN mkdir -p /app/runtime/chroma_data
RUN mkdir -p /app/logs

# Expose port mặc định
EXPOSE 8123

# Cấu hình biến môi trường
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Script khởi động mặc định
# Các tham số có thể được ghi đè khi chạy container
ENTRYPOINT ["python", "-m", "app.main"]
CMD ["--host", "0.0.0.0", "--port", "8123"] 