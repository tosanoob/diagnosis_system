from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class ReasoningPrompt:
    SYSTEM_PROMPT = """Bạn là bác sĩ da liễu, công việc của bạn là dựa vào thông tin được cung cấp, bao gồm triệu chứng mắc phải, hình ảnh bệnh, và các dữ liệu liên quan, tiến hành đưa ra suy luận và chẩn đoán sơ bộ"""
    USER_PROMPT = """Bệnh nhân có triệu chứng như sau:
    {has_text}
    
    {has_image}
    
    Sau đây là một số dữ liệu liên quan đến ca bệnh:
    {related_data}
    
    Hãy phân tích xem xét từng dữ liệu và kết luận các khả năng bệnh có thể mắc phải.
    Cung cấp chẩn đoán của bạn dựa trên các dữ liệu, sau cùng, khẳng định lần cuối các khả năng bệnh có thể mắc phải.
    Định dạng trả lời như sau:

    **Suy luận:** <Suy luận của bạn về bệnh nhân>
    **Chẩn đoán:** <Danh sách các tên bệnh mà bệnh nhân có thể mắc phải, tên bệnh là một trong các bệnh được cung cấp>
    """

    HAS_IMAGE = """Hình ảnh triệu chứng được đính kèm"""

    HAS_TEXT = """Triệu chứng được mô tả bằng văn bản:"""

    @staticmethod
    def format_prompt(text: str | None, image: str | None, related_data: str):
        has_text = ReasoningPrompt.HAS_TEXT + "\n" + text if text else ""
        has_image = ReasoningPrompt.HAS_IMAGE + "\n" + image if image else ""
        return ReasoningPrompt.USER_PROMPT.format(has_text=has_text, has_image=has_image, related_data=related_data) 