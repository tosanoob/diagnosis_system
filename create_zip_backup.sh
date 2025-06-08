#!/bin/bash

# Script để nén toàn bộ thư mục query_system thành file .tar.gz
# Tác giả: Auto-generated script
# Mô tả: Nén tất cả nội dung của thư mục hiện tại thành file .tar.gz

set -e  # Dừng script nếu có lỗi

# Lấy tên thư mục hiện tại
CURRENT_DIR=$(basename "$PWD")

# Tạo tên file với timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
TAR_NAME="${CURRENT_DIR}_backup_${TIMESTAMP}.tar.gz"

# Thông báo bắt đầu
echo "=========================================="
echo "🚀 Bắt đầu nén thư mục: $CURRENT_DIR"
echo "📁 File đích: $TAR_NAME"
echo "=========================================="

# Kiểm tra xem tar command có sẵn không
if ! command -v tar &> /dev/null; then
    echo "❌ Lỗi: Command 'tar' không được tìm thấy!"
    echo "📥 Tar thường có sẵn trên hầu hết hệ thống Linux"
    exit 1
fi

# Di chuyển lên thư mục cha để nén toàn bộ thư mục con
cd ..

# Tạo file .tar.gz, loại trừ các file/thư mục không cần thiết
echo "📦 Đang nén..."
tar -czf "$TAR_NAME" \
    --exclude="$CURRENT_DIR/.git" \
    --exclude="$CURRENT_DIR/__pycache__" \
    --exclude="$CURRENT_DIR/**/__pycache__" \
    --exclude="$CURRENT_DIR/*.pyc" \
    --exclude="$CURRENT_DIR/**/*.pyc" \
    --exclude="$CURRENT_DIR/logs" \
    --exclude="$CURRENT_DIR/.DS_Store" \
    --exclude="$CURRENT_DIR/**/.DS_Store" \
    --exclude="$CURRENT_DIR/node_modules" \
    --exclude="$CURRENT_DIR/**/node_modules" \
    --exclude="$CURRENT_DIR/.env" \
    --exclude="$CURRENT_DIR/.env.local" \
    "$CURRENT_DIR" 

# Kiểm tra kết quả
if [ $? -eq 0 ]; then
    # Lấy kích thước file
    FILE_SIZE=$(du -h "$TAR_NAME" | cut -f1)
    
    echo "=========================================="
    echo "✅ Nén thành công!"
    echo "📁 File: $TAR_NAME"
    echo "📏 Kích thước: $FILE_SIZE"
    echo "📍 Vị trí: $(pwd)/$TAR_NAME"
    echo "=========================================="
    
    # Di chuyển file .tar.gz vào thư mục gốc
    mv "$TAR_NAME" "$CURRENT_DIR/"
    cd "$CURRENT_DIR"
    
    echo "📁 File .tar.gz đã được di chuyển vào thư mục: $(pwd)/$TAR_NAME"
else
    echo "❌ Có lỗi xảy ra trong quá trình nén!"
    cd "$CURRENT_DIR"
    exit 1
fi

echo ""
echo "🎉 Hoàn thành! Bạn có thể tìm thấy file nén tại: ./$TAR_NAME" 