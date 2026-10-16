"""
schemas/interview.py — Pydantic schema cho bộ câu hỏi phỏng vấn do AI sinh (Structured Outputs, Mục 4.8)

Giống CVExtraction: không dùng giá trị mặc định (Gemini response_schema không hỗ trợ),
mỗi trường có description để mô hình hiểu đúng ý nghĩa.
"""
from typing import List, Literal

from pydantic import BaseModel, Field

QuestionCategory = Literal["skill_gap", "skill_verification", "experience", "behavioral"]


class InterviewQuestion(BaseModel):
    question: str = Field(..., description="Câu hỏi phỏng vấn bằng tiếng Việt, câu hỏi mở, cụ thể, gắn với tình huống thực tế của vị trí")
    category: QuestionCategory = Field(
        ...,
        description=(
            "skill_gap: khai thác kỹ năng JD yêu cầu mà CV còn thiếu; "
            "skill_verification: kiểm chứng kỹ năng CV chỉ đáp ứng gián tiếp/chưa rõ; "
            "experience: đào sâu kinh nghiệm dự án liên quan; behavioral: hành vi, tình huống làm việc"
        ),
    )
    target_skill: str = Field(..., description="Kỹ năng hoặc năng lực chính mà câu hỏi đánh giá (VD: 'FastAPI', 'Thiết kế CSDL')")
    purpose: str = Field(..., description="Mục đích của câu hỏi: HR/người phỏng vấn cần tìm hiểu điều gì (1 câu)")
    good_answer_hints: str = Field(..., description="Dấu hiệu của một câu trả lời tốt để người phỏng vấn đối chiếu (1-2 câu)")


class InterviewQuestionSet(BaseModel):
    """Bộ 3–5 câu hỏi phỏng vấn — lưu vào Application.interview_questions (chỉ nội dung câu hỏi)."""

    questions: List[InterviewQuestion] = Field(..., description="Từ 3 đến 5 câu hỏi, xếp theo mức độ ưu tiên giảm dần")
