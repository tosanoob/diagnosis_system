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
    model: str = "gemini-1.5-flash",
    temperature: float = 0.01,
    max_tokens: int = 1000
    ):
    """
    Sử dụng Gemini LLM để tạo nội dung từ hình ảnh.
    
    Args:
        image_base64: base64 string hoặc bytes
        system_instruction: Hướng dẫn hệ thống
        user_instruction: Hướng dẫn người dùng
        mime_type: Loại MIME của ảnh
        model: Tên mô hình
        temperature: Nhiệt độ
        max_tokens: Số token tối đa
        
    Returns:
        str: Kết quả trả về từ LLM
    """
    client = genai.Client(
        api_key=settings.GEMINI_API_KEY,
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

    try:
        result = client.models.generate_content(
            model=model,
            contents=contents,
            config=generate_content_config,
        )
        return result.text
    except Exception as e:
        logger.error(f"Lỗi khi sử dụng Gemini với ảnh: {str(e)}")
        return "Không thể phân tích ảnh."

def gemini_llm_request(
        system_instruction: str, 
        user_instruction: str, 
        model: str = "gemini-1.5-flash", 
        temperature: float = 0.0, 
        max_tokens: int = 1000,
        ) -> str:
    """
    Hàm gửi yêu cầu đến LLM
    
    Args:
        system_instruction: Hướng dẫn hệ thống
        user_instruction: Hướng dẫn người dùng
        model: Mô hình LLM
        temperature: Nhiệt độ
        max_tokens: Số token tối đa
        
    Returns:
        str: Kết quả trả về từ LLM
    """
    client = genai.Client(
        api_key=settings.GEMINI_API_KEY,
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

    try:
        result = client.models.generate_content(
            model=model,
            contents=contents,
            config=generate_content_config,
        )
        return result.text
    except Exception as e:
        logger.error(f"Lỗi khi sử dụng Gemini: {str(e)}")
        return "Không thể xử lý yêu cầu."

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