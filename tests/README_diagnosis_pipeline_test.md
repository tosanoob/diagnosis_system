# Diagnosis Pipeline Test

Script test pipeline chẩn đoán độc lập, mô phỏng đầy đủ logic API `image-only-multi-turn` mà không cần gọi API.

## Mô tả

Script này sẽ:
1. Chọn N samples ngẫu nhiên từ dataset SkinCAP
2. Tạo mô tả cho mỗi ảnh bằng Gemini API
3. Chạy pipeline chẩn đoán trực tiếp qua service functions:
   - `get_first_stage_diagnosis_v3()`: Stage 1 - Chẩn đoán ban đầu
   - `get_second_stage_diagnosis_v3()`: Stage 2 - Follow-up questions
4. Lưu kết quả và thống kê

## Yêu cầu

### Files cần thiết:
- `metadata-skincap.json`: Metadata của SkinCAP dataset
- `crossmap_SkinCAP.json`: Mapping từ SkinCAP labels sang standard labels

### Environment:
- Gemini API key: Set biến môi trường `GEMINI_API_KEY`
- Python packages: `datasets`, `google-genai`, `numpy`, `pillow`, `tqdm`

## Cách sử dụng

### 1. Chạy test đơn giản (2 samples):
```bash
cd tests/
python run_diagnosis_pipeline_test.py
```

### 2. Chạy test với tùy chọn:
```bash
cd tests/
python test_diagnosis_pipeline.py --samples 5 --output custom_results.json
```

### 3. Tùy chọn command line:
- `--samples N`: Số lượng samples test (default: 3)
- `--dataset NAME`: Tên dataset (default: "joshuachou/SkinCAP") 
- `--output FILE`: File output (default: auto-generated với timestamp)

## Cấu trúc kết quả

```json
{
  "test_info": {
    "timestamp": "2024-01-01T12:00:00",
    "dataset": "joshuachou/SkinCAP",
    "num_samples": 3,
    "test_type": "diagnosis_pipeline_direct_service_call"
  },
  "stats": {
    "total_samples": 3,
    "successful_samples": 2,
    "failed_samples": 1,
    "success_rate": 0.67
  },
  "results": [
    {
      "sample_index": 123,
      "original_label": "acne",
      "standard_label": "TRỨNG CÁ (Acne)",
      "generated_description": "Hình ảnh cho thấy...",
      "stage1_labels": [...],
      "stage1_response": "...",
      "stage2_response": "...",
      "chat_history_length": 4,
      "success": true,
      "error": null
    }
  ]
}
```

## So sánh với API

### API gọi qua requests:
```python
response = requests.post(
    "https://api.example.com/diagnosis/image-only-multi-turn",
    json={
        "image_base64": image_base64,
        "text": description,
        "chat_history": None
    }
)
```

### Direct service call:
```python
all_labels, response, chat_history = await get_first_stage_diagnosis_v3(
    image_base64=image_base64,
    text=description
)
```

## Lợi ích

1. **Độc lập**: Không cần hệ thống API running
2. **Nhanh hơn**: Không có network latency
3. **Debug dễ dàng**: Có thể debug trực tiếp trong service functions
4. **Test chi tiết**: Có thể test từng component riêng biệt
5. **Không ảnh hưởng hệ thống**: Chạy hoàn toàn độc lập

## Lưu ý

- Script cần file metadata và crossmap để chạy
- Cần Gemini API key để tạo description
- Mỗi sample có delay 5 giây để tránh rate limit
- Kết quả được lưu trong `tests/results/` với timestamp

## Troubleshooting

### Lỗi "metadata-skincap.json not found":
- Đảm bảo file metadata có trong working directory
- Hoặc tạo file metadata từ dataset

### Lỗi Gemini API:
- Kiểm tra API key
- Kiểm tra network connection
- Kiểm tra quota limit

### Lỗi import modules:
- Đảm bảo chạy từ thư mục tests/
- Kiểm tra sys.path trong script 