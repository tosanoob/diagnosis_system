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

    IMAGE_ONLY_SYSTEM_PROMPT = """Bạn là bác sĩ da liễu, công việc của bạn là dựa vào thông tin được cung cấp, bao gồm hình ảnh bệnh, và các dữ liệu liên quan, tiến hành đưa ra suy luận và chẩn đoán sơ bộ cho trường hợp của tôi.
Từ hình ảnh được cung cấp, hệ thống đã chọn ra được các bệnh khả dĩ nhất. 
Hãy dựa vào thông tin được cung cấp để tiến hành suy luận. Bạn có thể đặt câu hỏi với tôi để yêu cầu cung cấp thêm thông tin và đưa ra suy luận mấu chốt."""

    USER_PROMPT_FIRST = """Tôi có triệu chứng như sau:
{has_text}

{has_image}

Sau đây là một số thông tin về các bệnh mà tôi khả năng đã mắc phải:
{related_data}

Hãy phân tích xem xét các thông tin bệnh lý được cung cấp, suy luận và thực hiện một trong hai hành động sau:
- Đặt câu hỏi cho tôi: nếu bạn cảm thấy còn cần tôi cung cấp thêm thông tin để phục vụ cho chẩn đoán.
Trong trường hợp này, hãy đưa ra một số lập luận ngắn để bệnh nhân hiểu được vấn đề, và đặt câu hỏi để bệnh nhân cung cấp thêm thông tin.

- Đưa ra chẩn đoán cuối cùng: nếu bạn cảm thấy đã có đủ thông tin để đưa ra chẩn đoán cuối cùng.
Trong trường hợp này, hãy đưa ra lập luận mấu chốt từ các thông tin bạn có, và đưa ra chẩn đoán là tên bệnh cụ thể, thuộc một trong các bệnh được cung cấp.

Trả lời với văn phong tự nhiên, chuyên nghiệp, giống như đối thoại với người bệnh.
"""

    USER_PROMPT_LATER = """Phản hồi cho câu hỏi: {text}
Chú ý hãy trả lời với văn phong tự nhiên, chuyên nghiệp, giống như đối thoại với người bệnh.
"""

    @staticmethod
    def format_prompt(text: str | None, image: bool, related_data: str):
        has_text = ReasoningPrompt.HAS_TEXT + "\n" + text if text else ""
        has_image = ReasoningPrompt.HAS_IMAGE + "\n" if image else ""
        return ReasoningPrompt.USER_PROMPT.format(has_text=has_text, has_image=has_image, related_data=related_data) 
    
    @staticmethod
    def format_prompt_first(text: str | None, image: bool, related_data: str):
        has_text = ReasoningPrompt.HAS_TEXT + "\n" + text if text else ""
        has_image = ReasoningPrompt.HAS_IMAGE + "\n" if image else ""
        return ReasoningPrompt.USER_PROMPT_FIRST.format(has_text=has_text, has_image=has_image, related_data=related_data) 

    @staticmethod
    def format_prompt_later(text: str):
        return ReasoningPrompt.USER_PROMPT_LATER.format(text=text)
