"""
Service xử lý các tác vụ liên quan đến LLM
"""
import os
from google import genai
from google.genai import types
from openai import OpenAI
from typing import List, Dict
from app.constants.enums import QueryType
from app.core.config import settings
from app.core.logging import logger


class AllModelsFailedException(Exception):
    """Exception được throw khi tất cả models và API keys đều fail"""
    def __init__(self, errors: Dict[str, Dict[str, str]]):
        self.errors = errors  # {api_key: {model: error_message}}
        error_msg = "Tất cả API keys và models đều fail:\n"
        for api_key, model_errors in errors.items():
            error_msg += f"API Key {api_key[:8]}***:\n"
            for model, error in model_errors.items():
                error_msg += f"  - {model}: {error}\n"
        super().__init__(error_msg)


def try_gemini_models_with_fallback(func, *args, **kwargs):
    """
    Helper function để thử nghiệm các Gemini API keys và models với fallback
    
    Args:
        func: Function cần execute với model và api_key (expect model_name, api_key là 2 parameters đầu tiên)
        *args, **kwargs: Arguments cho function
        
    Returns:
        Kết quả từ combination (api_key, model) thành công đầu tiên
        
    Raises:
        AllModelsFailedException: Khi tất cả API keys và models đều fail
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
                # logger.app_info(f"Thử nghiệm API key {api_key[:8]}*** với model: {model}")
                # Pass model và api_key như là 2 positional arguments đầu tiên
                result = func(model, api_key, *args, **kwargs)
                # logger.app_info(f"API key {api_key[:8]}*** với model {model} thành công")
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


def embedding_request(texts: List[str]) -> List[List[float]]:
    """
    Tạo embedding từ văn bản sử dụng BAAI/bge-m3
    
    Args:
        texts: Danh sách văn bản cần tạo embedding
        
    Returns:
        List[List[float]]: Danh sách vector embedding
    """
    client = OpenAI(base_url=settings.EMBEDDING_URL,
                    api_key=settings.EMBEDDING_API_KEY)
    result = client.embeddings.create(
        input=texts,
        model=settings.EMBEDDING_MODEL
    )
    embeddings = [response.embedding for response in result.data]
    return embeddings

def generate_with_image(
    image_base64, 
    system_instruction: str, 
    user_instruction: str, 
    mime_type: str = "image/jpeg",
    model: str = None,
    temperature: float = 0.01,
    max_tokens: int = 1000
    ):
    """
    Sử dụng Gemini LLM để tạo nội dung từ hình ảnh với fallback models.
    
    Args:
        image_base64: base64 string hoặc bytes
        system_instruction: Hướng dẫn hệ thống
        user_instruction: Hướng dẫn người dùng
        mime_type: Loại MIME của ảnh
        model: Tên mô hình (nếu None sẽ dùng fallback logic)
        temperature: Nhiệt độ
        max_tokens: Số token tối đa
        
    Returns:
        str: Kết quả trả về từ LLM
        
    Raises:
        AllModelsFailedException: Khi tất cả models đều fail
    """
    def _generate_with_single_model(model_name, api_key):
        client = genai.Client(
                api_key=api_key,
        )

        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_bytes(data=image_base64, mime_type=mime_type),
                    types.Part.from_text(text=user_instruction),
                ],
            )
        ]
        generate_content_config = types.GenerateContentConfig(
            response_mime_type="text/plain",
            system_instruction=[
                types.Part.from_text(text=system_instruction),
            ],
            temperature=temperature,
            max_output_tokens=max_tokens
        )

        result = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=generate_content_config,
        )
        return result.text

    # Nếu có model cụ thể được chỉ định, chỉ sử dụng model đó với API key đầu tiên
    if model:
        try:
            api_key = settings.GEMINI_API_KEYS[0]  # Sử dụng API key đầu tiên
            return _generate_with_single_model(model, api_key)
        except Exception as e:
                logger.error(f"Lỗi khi sử dụng Gemini với ảnh (model {model}): {str(e)}")
                raise e
    
    # Nếu không có model cụ thể, sử dụng fallback logic với tất cả API keys và models
    try:
        return try_gemini_models_with_fallback(_generate_with_single_model)
    except AllModelsFailedException as e:
        logger.error(f"Tất cả Gemini API keys và models đều fail: {str(e)}")
        raise e

def openai_to_gemini_history(history: List[Dict]) -> List[types.Content]:
    """
    Chuyển đổi lịch sử chat từ OpenAI sang định dạng Gemini
    OpenAI:
    [
        {
            "role": "user",
            "content": [{
                "type": "text",
                "text": "Hello, how are you?"
            },
            {
                "type": "image",
                "mime_type": "image/jpeg",
                "image": "<base64_image>"
            }
            ]
        },
        {
            "role": "assistant",
            "content": {
                "type": "text",
                "text": "I'm doing well, thank you!"
            }
        }
    ]
    Gemini:
    [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text="Hello, how are you?"),
                types.Part.from_image(image=image_base64)
            ]
        ),
        types.Content(
            role="model",
            parts=[
                types.Part.from_text(text="I'm doing well, thank you!")
            ]
        )
    ]
    """
    gemini_history = []
    for item in history:
        if item["role"] == "user":
            gemini_role = "user"
        elif item["role"] == "assistant":
            gemini_role = "model"
        gemini_content_parts = []
        if isinstance(item["content"], list):
            for content in item["content"]:
                if content["type"] == "text":
                    gemini_content_parts.append(types.Part.from_text(text=content["text"]))
                elif content["type"] == "image":
                    gemini_content_parts.append(types.Part.from_bytes(data=content["image"], mime_type=content["mime_type"]))
        gemini_history.append(types.Content(role=gemini_role, parts=gemini_content_parts))
    return gemini_history

def get_gemini_config(
    temperature: float = 0.0,
    max_tokens: int = 5000,
    response_mime_type: str = "text/plain",
    system_instruction: str = "",
) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        response_mime_type=response_mime_type,
        system_instruction=[
            types.Part.from_text(text=system_instruction),
        ],
        temperature=temperature,
        max_output_tokens=max_tokens
    )

def general_gemini_request(
    model: str = None,  # Thay đổi từ settings.GEMINI_MODEL
    contents: List[types.Content] = [],
    config: types.GenerateContentConfig = None
) -> str:
    """
    Gửi yêu cầu đến Gemini LLM với fallback models
    
    Args:
        model: Tên model cụ thể (nếu None sẽ dùng fallback logic)
        contents: Nội dung chat
        config: Cấu hình generate
        
    Returns:
        str: Kết quả từ LLM
        
    Raises:
        AllModelsFailedException: Khi tất cả models đều fail
    """
    def _request_with_single_model(model_name, api_key):
        client = genai.Client(
                api_key=api_key,
        )
        result = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=config,
        )
        return result.text

    # Nếu có model cụ thể được chỉ định, chỉ sử dụng model đó với API key đầu tiên
    if model:
        try:
            api_key = settings.GEMINI_API_KEYS[0]  # Sử dụng API key đầu tiên
            return _request_with_single_model(model, api_key)
        except Exception as e:
            logger.error(f"Lỗi khi sử dụng Gemini (model {model}): {str(e)}")
            raise e
    
    # Nếu không có model cụ thể, sử dụng fallback logic với tất cả API keys và models
    try:
        return try_gemini_models_with_fallback(_request_with_single_model)
    except AllModelsFailedException as e:
        logger.error(f"Tất cả Gemini API keys và models đều fail: {str(e)}")
        raise e

def gemini_llm_request(
        system_instruction: str, 
        user_instruction: str, 
        model: str = None,  # Thay đổi từ settings.GEMINI_MODEL
        temperature: float = 0.0, 
        max_tokens: int = 1000,
        ) -> str:
    """
    Hàm gửi yêu cầu đến LLM với fallback models
    
    Args:
        system_instruction: Hướng dẫn hệ thống
        user_instruction: Hướng dẫn người dùng
        model: Mô hình LLM cụ thể (nếu None sẽ dùng fallback logic)
        temperature: Nhiệt độ
        max_tokens: Số token tối đa
        
    Returns:
        str: Kết quả trả về từ LLM
        
    Raises:
        AllModelsFailedException: Khi tất cả models đều fail
    """
    def _request_with_single_model(model_name, api_key):
        client = genai.Client(
                api_key=api_key,
        )
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=user_instruction),
                ],
            )
        ]
        generate_content_config = types.GenerateContentConfig(
            response_mime_type="text/plain",
            system_instruction=[
                types.Part.from_text(text=system_instruction),
            ],
            temperature=temperature,
            max_output_tokens=max_tokens
        )

        result = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=generate_content_config,
        )
        return result.text

    # Nếu có model cụ thể được chỉ định, chỉ sử dụng model đó với API key đầu tiên
    if model:
        try:
            api_key = settings.GEMINI_API_KEYS[0]  # Sử dụng API key đầu tiên
            return _request_with_single_model(model, api_key)
        except Exception as e:
            logger.error(f"Lỗi khi sử dụng Gemini (model {model}): {str(e)}")
            raise e
    
    # Nếu không có model cụ thể, sử dụng fallback logic với tất cả API keys và models
    try:
        return try_gemini_models_with_fallback(_request_with_single_model)
    except AllModelsFailedException as e:
        logger.error(f"Tất cả Gemini API keys và models đều fail: {str(e)}")
        raise e

def extract_keywords(text: str) -> List[str]:
    """
    Hàm trích xuất từ khóa từ câu hỏi
    
    Args:
        text: Câu hỏi cần trích xuất từ khóa
        
    Returns:
        list[str]: Danh sách từ khóa
    """
    retries = 3
    for _ in range(retries):
        try:
            system_prompt = """# Vai trò: Bạn là một chuyên gia y khoa, đặc biệt là trong lĩnh vực da liễu.

# Mục tiêu: Trích xuất tất cả các khái niệm hoặc thực thể liên quan đến chủ đề y khoa quan trọng trong văn bản input.

# Các thực thể có thể là bệnh tật, triệu chứng, nguyên nhân/yếu tố nguy cơ, vị trí giải phẫu nơi tổn thương xuất hiện, v.v.

# Output: A python list of entities, wrapped in triple backticks: ```python```

# Example:
Input: "Tôi bị nổi mẩn ngứa ở tay và chân, cảm thấy ngứa rát khó chịu."

Output: ```python
['nổi mẩn ngứa', 'tay', 'chân', 'ngứa rát']
```

---

Input: "Tôi muốn biết thêm về bệnh vảy nến, những nguyên nhân nào gây nên bệnh này?"

Output: ```python
['vảy nến']
```
"""
            user_prompt = f"Trích xuất các từ khóa chuyên môn liên quan đến bệnh lý da liễu, bao gồm triệu chứng, nghi bệnh, các yếu tố có thể liên quan đến bệnh từ đoạn input sau: {text}"
            response = gemini_llm_request(
                system_instruction=system_prompt,
                user_instruction=user_prompt
            )
            if response.startswith("```python"):
                response = response[len("```python"):-len("```")-1]
            return eval(response)
        except Exception as e:
            logger.error(f"Lỗi khi trích xuất từ khóa (thử lại {_+1}/{retries}): {str(e)}")
            logger.error(f"Response gây lỗi: {response}")
            continue
    return []


def detect_query_type(text: str) -> Dict:
    """
    Hàm phát hiện loại truy vấn từ text
    
    Args:
        text: Câu hỏi cần phát hiện loại truy vấn
        
    Returns:
        Dict: Loại truy vấn (thuộc một trong các loại trong QueryType)
    """
    retries = 3
    for _ in range(retries):
        try:
            system_prompt = """# Vai trò: Bạn là một phân loại logic, với kiến thức về lĩnh vực y khoa.  
# Mục tiêu: Cho một câu hỏi, phân loại nó thành một trong các loại sau:
- Tìm kiếm phương pháp điều trị cho một bệnh => disease_treatments
- Tìm kiếm triệu chứng của một bệnh => disease_symptoms
- Tìm kiếm nguyên nhân/yếu tố nguy cơ cho một bệnh => disease_causes
- Tìm kiếm bệnh tật ảnh hưởng đến một phần giải phẫu => diseases_by_anatomy
- Tìm kiếm bệnh tật dựa trên triệu chứng => diseases_by_symptom
- Tìm kiếm các bệnh tương tự cho một bệnh, chia sẻ một số triệu chứng chung => similar_diseases

# Output: Một loại truy vấn cụ thể để thực hiện.

# Example:
Input: "Tôi muốn biết thêm về bệnh vảy nến, những nguyên nhân nào gây nên bệnh này?"

Output: "disease_causes"

Input: "Có những bệnh nào có phát sinh triệu chứng nổi mẩn đỏ và ngứa?"

Output: "diseases_by_symptom"
"""
            user_prompt = f"Given a question, classify it into one of the following types: {text}"
            response = gemini_llm_request(
                system_instruction=system_prompt,
                user_instruction=user_prompt
            )
            
            return {
                "query_type": response.strip().strip("\"'"),
                "query_text": text
            }
        except Exception as e:
            logger.error(f"Lỗi khi phát hiện loại truy vấn (thử lại {_+1}/{retries}): {str(e)}")
            continue
    return {"query_type": "unknown", "query_text": text}


def get_image_caption(image_base64: str) -> str:
    """
    Lấy mô tả từ ảnh
    
    Args:
        image_base64: Chuỗi base64 của ảnh
        
    Returns:
        str: Mô tả ảnh
    """
    system_prompt = """Bạn là một bác sĩ da liễu có kinh nghiệm. Nhiệm vụ của bạn là mô tả chi tiết những gì bạn thấy trong hình ảnh về da liễu này để phục vụ cho việc chẩn đoán.
Hãy tập trung vào:
1. Vị trí của tổn thương
2. Kích thước của tổn thương
3. Màu sắc của tổn thương
4. Hình dạng, viền, và bề mặt của tổn thương
5. Bất kỳ thay đổi nào so với da bình thường xung quanh
6. Mô tả có cấu trúc và toàn diện

Không đưa ra chẩn đoán hoặc điều trị. Chỉ mô tả những gì quan sát được trong hình ảnh."""
    user_prompt = "Mô tả chi tiết những gì bạn thấy trong hình ảnh y khoa này."
    
    caption = generate_with_image(
        image_base64=image_base64,
        system_instruction=system_prompt,
        user_instruction=user_prompt
    )
    
    return caption

def llm_score_labels(image_base64: str, labels: List[str], top_k: int = 5) -> List[str]:
    """
    Chọn các nhãn có khả năng cao nhất từ danh sách các nhãn
    """
    system_prompt = """Bạn là mô hình phân loại và chẩn đoán hình ảnh bệnh da liễu. 
Nhiệm vụ của bạn là xác định xác suất phần trăm các nhãn bệnh từ danh sách nhãn bệnh (labels) và hình ảnh được cung cấp."""
    user_prompt = f"""Dựa vào hình ảnh được cung cấp, hãy đưa ra xác suất phần trăm các nhãn bệnh từ danh sách nhãn bệnh sau: 
{labels}

Định dạng output:
```python
[
    {{
        "label": "Bệnh tật",
        "probability": 0.95
    }},
    {{
        "label": "Bệnh tật khác",
        "probability": 0.05
    }}
]
```

Chỉ phản hồi theo đúng định dạng output, không có bất kỳ text nào khác.
"""
    caption = generate_with_image(
        image_base64=image_base64,
        system_instruction=system_prompt,
        user_instruction=user_prompt
    )
    
    return caption