# 6.8 – Kỹ năng trùng khớp, kỹ năng còn thiếu, câu hỏi phỏng vấn gợi ý

**Ngày:** 17/10/2026 · **Nhánh:** `feature/frontend-tan` · **Màn hình:** A9 (tab *Kỹ năng*, tab *Câu hỏi phỏng vấn*) · Làm chung với [6.7](Phan%206.7.md)

## Mục tiêu
Trong modal hồ sơ, hiện rõ kỹ năng nào khớp, kỹ năng nào còn thiếu, và các câu hỏi phỏng vấn AI gợi ý.

## Đã làm
- **Tab Kỹ năng:**
  - **Đáp ứng** (nhãn xanh, `matched_skills`). Kỹ năng khớp gián tiếp (`scoring_details.skill_matches[].match_type` là `semantic` / `alias`) có ghi chú "tương đương: …" (`matched_with`).
  - **Bắt buộc còn thiếu** (nhãn đỏ, `missing_skills`).
  - **Ưu tiên còn thiếu** (nhãn vàng, `scoring_details.missing_preferred_skills`).
  - Mỗi nhóm có số lượng; rỗng thì ghi "Không thiếu…" / "Chưa có kỹ năng nào khớp".
  - Trên tab có nhãn đỏ "N thiếu" khi thiếu kỹ năng bắt buộc.
- **Tab Câu hỏi phỏng vấn:**
  - Ưu tiên `ai_extracted_info.interview_details.questions[]`; không có thì dùng `interview_questions` (mảng chuỗi của hồ sơ cũ).
  - Mỗi câu có số thứ tự và nhãn loại tiếng Việt: Kỹ năng còn thiếu (đỏ), Kiểm chứng kỹ năng (xanh dương), Kinh nghiệm (tím), Tình huống (xanh lá).
  - Bấm vào câu (accordion) để xem **kỹ năng nhắm tới**, **mục đích**, **gợi ý câu trả lời tốt**. Câu không có phần mở rộng thì không có mũi tên, không bấm được.
  - Trên tab có số câu hỏi.

## File thay đổi
Xem [6.7](Phan%206.7.md#file-thay-đổi-chung-67–68): các hàm `skillsHtml`, `interviewQuestions`, `questionsHtml`; CSS `.skill-chip`, `.question-item`.

## Kiểm thử
Xem bảng chung ở [6.7](Phan%206.7.md#kiểm-thử-chung-67–68). Riêng 6.8:
- Dữ liệu thật hồ sơ #57: 7 kỹ năng đáp ứng, 0 thiếu; 4 câu hỏi có nhãn (3 *Kinh nghiệm*, 1 *Tình huống*), mở ra đủ kỹ năng / mục đích / gợi ý.
- Giả lập: kỹ năng khớp gián tiếp có ghi chú "tương đương"; thiếu 1 kỹ năng → nhãn tab "1 thiếu"; câu hỏi dạng chuỗi; mọi trường `null`; XSS.

## Lưu ý
- Chất lượng câu hỏi phụ thuộc AI. Với Ollama `qwen2.5:7b` có thể kém hơn ([Issue 08](../Issues/08-qwen-cau-hoi-phong-van-chat-luong-thap.md)); phần này do backend xử lý.
