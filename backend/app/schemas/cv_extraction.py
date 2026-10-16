"""
schemas/cv_extraction.py — Pydantic schema cho kết quả Gemini bóc tách CV (Structured Outputs)

Schema này được truyền làm response_schema cho Gemini nên:
- Không dùng giá trị mặc định (Gemini API không hỗ trợ default trong response schema).
- Trường không chắc chắn có trong CV khai báo Optional (cho phép null) thay vì bỏ trống.
- Mô tả (description) của từng trường được gửi kèm giúp mô hình hiểu đúng ý nghĩa.
"""
from typing import List, Optional

from pydantic import BaseModel, Field


class WorkExperience(BaseModel):
    company: str = Field(..., description="Tên công ty / tổ chức")
    position: str = Field(..., description="Chức danh / vị trí đảm nhiệm")
    start_date: Optional[str] = Field(..., description="Thời điểm bắt đầu, định dạng YYYY-MM hoặc YYYY; null nếu không rõ")
    end_date: Optional[str] = Field(..., description="Thời điểm kết thúc YYYY-MM hoặc YYYY; 'present' nếu đang làm; null nếu không rõ")
    description: Optional[str] = Field(..., description="Tóm tắt ngắn công việc / thành tựu chính (tối đa 2 câu)")


class Education(BaseModel):
    institution: str = Field(..., description="Tên trường / cơ sở đào tạo")
    degree: Optional[str] = Field(..., description="Bậc học: Cử nhân, Kỹ sư, Thạc sĩ, Cao đẳng, Chứng chỉ...")
    major: Optional[str] = Field(..., description="Chuyên ngành")
    graduation_year: Optional[int] = Field(..., description="Năm tốt nghiệp (hoặc dự kiến), null nếu không rõ")
    gpa: Optional[str] = Field(..., description="Điểm GPA nguyên văn như trong CV (VD: '3.2/4', '8.1/10'), null nếu không có")


class CVExtraction(BaseModel):
    """Thông tin CV đã chuẩn hóa — lưu vào Application.ai_extracted_info."""

    full_name: Optional[str] = Field(..., description="Họ tên đầy đủ của ứng viên, viết đúng dấu tiếng Việt")
    email: Optional[str] = Field(..., description="Email liên hệ")
    phone: Optional[str] = Field(..., description="Số điện thoại liên hệ")
    location: Optional[str] = Field(..., description="Địa chỉ / thành phố sinh sống")
    current_title: Optional[str] = Field(..., description="Chức danh hiện tại hoặc vị trí ứng tuyển ghi trên CV")
    summary: str = Field(..., description="Tóm tắt khách quan 2-3 câu về hồ sơ ứng viên, bằng tiếng Việt")
    skills: List[str] = Field(..., description="Danh sách kỹ năng chuyên môn / công nghệ, mỗi phần tử là một kỹ năng, giữ tên chuẩn (VD: Python, ReactJS, MySQL, Docker)")
    soft_skills: List[str] = Field(..., description="Kỹ năng mềm (giao tiếp, làm việc nhóm...)")
    experience_years: float = Field(..., description="Tổng số năm kinh nghiệm làm việc chuyên môn (thực tập tính theo thời gian thực tế); 0 nếu chưa có kinh nghiệm")
    experience_years_stated: Optional[float] = Field(..., description="Số năm kinh nghiệm do chính CV ghi rõ bằng chữ (VD: 'hơn 3 năm kinh nghiệm', '5+ years of experience' → 3, 5); null nếu CV không ghi")
    work_experience: List[WorkExperience] = Field(..., description="Kinh nghiệm làm việc, mới nhất trước")
    education: List[Education] = Field(..., description="Quá trình học vấn, mới nhất trước")
    certifications: List[str] = Field(..., description="Chứng chỉ (VD: AWS SAA, TOEIC 850, IELTS 7.0)")
    languages: List[str] = Field(..., description="Ngoại ngữ kèm trình độ nếu có (VD: 'Tiếng Anh - TOEIC 750')")
