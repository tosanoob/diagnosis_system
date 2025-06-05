# Hướng dẫn Multiple API Keys cho Gemini

## Tổng quan

Hệ thống đã được mở rộng để hỗ trợ **multiple API keys** với fallback logic. Khi một API key fail với tất cả models, hệ thống sẽ tự động chuyển sang API key tiếp theo.

**Chiến lược fallback**: 
```
API_KEY_1 → [model1, model2, model3] 
   ↓ (nếu tất cả fail)
API_KEY_2 → [model1, model2, model3]
   ↓ (nếu tất cả fail)  
API_KEY_3 → [model1, model2, model3]
```

## Cấu hình Environment

### Cách 1: JSON String (Khuyến nghị)
```env
# Multiple API keys
GEMINI_API_KEYS='["key1","key2","key3"]'
GEMINI_MODELS='["gemini-1.5-flash","gemini-1.5-pro"]'
```

### Cách 2: Comma-separated String
```env
# Multiple API keys
GEMINI_API_KEYS="key1,key2,key3"
GEMINI_MODELS="gemini-1.5-flash,gemini-1.5-pro"
```

### Cách 3: Backward Compatibility
```env
# Single API key (sẽ được convert thành list)
GEMINI_API_KEY="your-single-key"
GEMINI_MODELS="gemini-1.5-flash,gemini-1.5-pro"
```

## Ví dụ cấu hình .env

```env
# API Keys - Multiple keys cho fallback
GEMINI_API_KEYS='["AIzaSyXXXXXXXXXXXXXXXXXXXXX","AIzaSyYYYYYYYYYYYYYYYYYYYYY","AIzaSyZZZZZZZZZZZZZZZZZZZZZ"]'

# Models - Danh sách models để thử với mỗi API key
GEMINI_MODELS='["gemini-1.5-flash","gemini-1.5-pro","gemini-1.0-pro"]'

# Other configs...
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
```

## Lợi ích

1. **Fault tolerance cao hơn**: Không bị gián đoạn khi một API key fail
2. **Load balancing tự động**: Phân tải qua nhiều API keys
3. **Cost optimization**: Có thể sử dụng API keys khác nhau cho các mục đích khác nhau
4. **Backward compatibility**: Code cũ vẫn hoạt động

## Error Handling

```python
try:
    response = gemini_llm_request(
        system_instruction=system_prompt,
        user_instruction=user_prompt
    )
except AllModelsFailedException as e:
    # e.errors = {api_key: {model: error_message}}
    logger.error(f"Tất cả API keys và models fail:")
    for api_key, model_errors in e.errors.items():
        logger.error(f"API Key {api_key[:8]}***:")
        for model, error in model_errors.items():
            logger.error(f"  - {model}: {error}")
```

## Validation Rules

- ✅ JSON string: `'["key1","key2"]'`
- ✅ Comma-separated: `"key1,key2,key3"`
- ✅ Single key: `"key1"` (sẽ thành `["key1"]`)
- ✅ Fallback to GEMINI_API_KEY nếu GEMINI_API_KEYS không set
- ❌ Empty: `""` hoặc `[]`

## Migration từ Single API Key

### Trước:
```env
GEMINI_API_KEY="your-api-key"
GEMINI_MODEL="gemini-1.5-flash"
```

### Sau:
```env
# Option 1: Multiple keys
GEMINI_API_KEYS='["key1","key2","key3"]'
GEMINI_MODELS='["gemini-1.5-flash","gemini-1.5-pro"]'

# Option 2: Keep single key (backward compatible)
GEMINI_API_KEY="your-api-key"
GEMINI_MODELS='["gemini-1.5-flash","gemini-1.5-pro"]'
``` 