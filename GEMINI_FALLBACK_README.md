# Hệ thống Fallback Models và API Keys cho Gemini

## Tổng quan

Hệ thống đã được cập nhật để hỗ trợ **fallback cả API keys và models** cho Gemini API. Thay vì chỉ sử dụng một API key và model duy nhất, hệ thống sẽ thử nghiệm lần lượt từng API key với tất cả models, và chuyển sang API key tiếp theo nếu tất cả models của API key trước fail.

**Chiến lược fallback**: API_KEY_1 → [model1, model2, model3] → API_KEY_2 → [model1, model2, model3] → ...

## Thay đổi chính

### 1. Cấu hình (config.py)

```python
# Trước (single API key và models)
GEMINI_API_KEY: str = "your-api-key"
GEMINI_MODEL: str = "gemini-1.5-flash"

# Sau (multiple API keys và models)
GEMINI_API_KEY: Optional[str] = None  # Backward compatibility
GEMINI_API_KEYS: Union[str, List[str]] = None  # New: Multiple API keys
GEMINI_MODELS: Union[str, List[str]] = '["gemini-1.5-flash","gemini-1.5-pro","gemini-1.0-pro"]'
```

### 2. Exception mới

```python
class AllModelsFailedException(Exception):
    """Exception được throw khi tất cả API keys và models đều fail"""
    def __init__(self, errors: Dict[str, Dict[str, str]]):
        self.errors = errors  # {api_key: {model: error_message}}
```

### 3. Functions được cập nhật

- `generate_with_image()`: Hỗ trợ fallback qua API keys và models
- `general_gemini_request()`: Hỗ trợ fallback qua API keys và models
- `gemini_llm_request()`: Hỗ trợ fallback qua API keys và models

## Cách hoạt động

### 1. Logic Fallback

```python
def try_gemini_models_with_fallback(func, *args, **kwargs):
    """
    Helper function để thử nghiệm các Gemini API keys và models với fallback
    
    Args:
        func: Function cần execute với model và api_key (expect model_name, api_key là 2 parameters đầu tiên)
        *args, **kwargs: Arguments cho function
    """
    errors = {}
    
    # Lấy danh sách API keys từ config
    api_keys = settings.GEMINI_API_KEYS
    models = settings.GEMINI_MODELS
    
    # Thử từng API key với tất cả models
    for api_key in api_keys:
        api_key_errors = {}
        
        for model in models:
            try:
                logger.app_info(f"Thử nghiệm API key {api_key[:8]}*** với model: {model}")
                # Pass model và api_key như là 2 positional arguments đầu tiên
                result = func(model, api_key, *args, **kwargs)
                logger.app_info(f"API key {api_key[:8]}*** với model {model} thành công")
                return result
            except Exception as e:
                error_msg = str(e)
                api_key_errors[model] = error_msg
                logger.app_info(f"API key {api_key[:8]}*** với model {model} fail: {error_msg}")
                continue
        
        # Lưu errors của API key này
        errors[api_key] = api_key_errors
    
    # Nếu tất cả API keys và models đều fail
    raise AllModelsFailedException(errors)
```

### 2. Sử dụng model cụ thể

```python
# Sử dụng model cụ thể (sẽ dùng API key đầu tiên)
response = generate_with_image(
    image_base64=image,
    system_instruction=system_prompt,
    user_instruction=user_prompt,
    model="gemini-1.5-pro"  # Model cụ thể với API key đầu tiên
)

# Sử dụng fallback logic (thử tất cả API keys và models)
response = generate_with_image(
    image_base64=image,
    system_instruction=system_prompt,
    user_instruction=user_prompt,
    model=None  # Hoặc bỏ qua parameter này
)
```

## Lợi ích

1. **Độ tin cậy cao hơn**: Hệ thống không bị gián đoạn khi một API key và model fail
2. **Tự động chuyển đổi**: Không cần can thiệp thủ công khi API key và model fail
3. **Logging chi tiết**: Theo dõi được API key và model nào thành công/fail
4. **Linh hoạt**: Có thể chỉ định API key và model cụ thể khi cần thiết

## Cấu hình Environment

Bạn có thể cấu hình danh sách API keys và models theo **3 cách**:

### Cách 1: JSON String (Khuyến nghị)
```env
# Trong file .env
GEMINI_MODELS='["gemini-1.5-flash","gemini-1.5-pro","gemini-1.0-pro"]'
```

### Cách 2: Comma-separated String
```env
# Trong file .env
GEMINI_MODELS="gemini-1.5-flash,gemini-1.5-pro,gemini-1.0-pro"
```

### Cách 3: Default trong Code
```python
# Không cần set env variable, sử dụng default trong config.py
GEMINI_MODELS: Union[str, List[str]] = '["gemini-1.5-flash","gemini-1.5-pro","gemini-1.0-pro"]'
```

### Ví dụ cấu hình file .env:
```env
# API Keys
GEMINI_API_KEY=your_gemini_api_key_here

# Models fallback (chọn một trong các cách sau)
# Cách 1: JSON (khuyến nghị)
GEMINI_MODELS='["gemini-1.5-flash","gemini-1.5-pro"]'

# Cách 2: Comma-separated
# GEMINI_MODELS="gemini-1.5-flash,gemini-1.5-pro"

# Cách 3: Single model (sẽ được convert thành list)
# GEMINI_MODELS="gemini-1.5-flash"
```

### Validation Rules:
- ✅ JSON string: `'["model1","model2"]'`
- ✅ Comma-separated: `"model1,model2,model3"`
- ✅ Single model: `"model1"` (sẽ thành `["model1"]`)
- ❌ Empty string: `""`
- ❌ Invalid JSON: `'["model1"'`

## Error Handling

```python
try:
    response = gemini_llm_request(
        system_instruction=system_prompt,
        user_instruction=user_prompt
    )
except AllModelsFailedException as e:
    logger.error(f"Tất cả API keys và models fail: {e}")
    # Handle fallback logic hoặc return error response
```

## Migration Guide

### Trước khi update:
```python
# Code cũ vẫn hoạt động nhưng deprecated
response = gemini_llm_request(
    system_instruction=system_prompt,
    user_instruction=user_prompt,
    model=settings.GEMINI_MODEL  # ❌ Không còn tồn tại
)
```

### Sau khi update:
```python
# Code mới - tự động fallback
response = gemini_llm_request(
    system_instruction=system_prompt,
    user_instruction=user_prompt
    # model=None (default) - sử dụng fallback logic
)

# Hoặc chỉ định API key và model cụ thể
response = gemini_llm_request(
    system_instruction=system_prompt,
    user_instruction=user_prompt,
    model="gemini-1.5-flash"  # Model cụ thể với API key đầu tiên
)
``` 