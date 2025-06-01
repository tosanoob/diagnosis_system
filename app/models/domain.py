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
Hãy dựa vào thông tin được cung cấp để tiến hành suy luận. Bạn buộc phải đưa ra kết luận cụ thể thay vì chỉ nói mơ hồ về tình trạng.
Suy luận của bạn có thể không chính xác, nhưng sẽ giúp ích rất nhiều cho bệnh nhân, vì vậy đừng ngần ngại mà nêu ra suy luận của mình.
Trả lời với văn phong tự nhiên, chuyên nghiệp, giống như đối thoại với người bệnh.
"""

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

    USER_PROMPT_FIRST_DIAGNOSIS_V3 = """Tôi có triệu chứng như sau:
{has_text}

{has_image}

Sau đây là một số thông tin về các bệnh da liễu thường gặp:
{related_data}

Hãy phân tích xem xét các thông tin bệnh lý được cung cấp, đưa ra suy luận và đề cập đến các bệnh mà khả năng cao tôi đã mắc phải.
Hãy chú ý nhấn mạnh các tên bệnh được đưa ra bằng cặp tag <diagnosis> và </diagnosis>.
Tên bệnh trong cặp tag <diagnosis> và </diagnosis> cần phải giống CHÍNH XÁC với một trong các bệnh đề cập ở trên, không viết tắt.
Ví dụ:
'... Dựa vào các triệu chứng của bệnh nhân, tôi nghĩ bệnh nhân có thể mắc phải <diagnosis>BỆNH LAO DA</diagnosis>...'

Trả lời với văn phong tự nhiên, chuyên nghiệp, giống như đối thoại với người bệnh.
Hãy đảm bảo liệt kê đầy đủ các bệnh khả thi, không bỏ sót, nhưng không dư thừa.
"""

    USER_PROMPT_ANALYZE_DIAGNOSIS_V3 = """Bệnh nhân khám bệnh có triệu chứng như sau:
{has_text}

{has_image}

Hệ thống gợi ý đã tìm kiếm được những thông tin bệnh với khả năng cao nhất:
{related_data}

Hãy phân tích trường hợp của bệnh nhân, dựa trên mô tả, hình ảnh và các thông tin bệnh được cung cấp, đưa ra chẩn đoán sơ bộ và giải thích cho bệnh nhân về tình trạng bệnh của họ.
Đồng thời, nếu bạn cảm thấy trường hợp là nghiêm trọng, hãy đề xuất bệnh nhân đến khám ở các cơ sở y tế.
Trả lời với văn phong tự nhiên, chuyên nghiệp, giống như đối thoại với người bệnh.
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
    
    @staticmethod
    def format_prompt_v3(text: str | None, image: bool, related_data: str):
        has_text = ReasoningPrompt.HAS_TEXT + "\n" + text if text else ""
        has_image = ReasoningPrompt.HAS_IMAGE + "\n" if image else ""
        return ReasoningPrompt.USER_PROMPT_FIRST_DIAGNOSIS_V3.format(has_text=has_text, has_image=has_image, related_data=related_data) 
    
    @staticmethod
    def format_prompt_analyze_diagnosis_v3(text: str | None, image: bool, related_data: str):
        has_text = ReasoningPrompt.HAS_TEXT + "\n" + text if text else ""
        has_image = ReasoningPrompt.HAS_IMAGE + "\n" if image else ""
        return ReasoningPrompt.USER_PROMPT_ANALYZE_DIAGNOSIS_V3.format(has_text=has_text, has_image=has_image, related_data=related_data) 