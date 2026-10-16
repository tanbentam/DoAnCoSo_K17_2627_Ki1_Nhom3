Các nội dung đã hoàn thành (Mục 4.8 — sinh 3–5 câu hỏi phỏng vấn khai thác lỗ hổng kỹ năng):

## Schema câu hỏi (backend/app/schemas/interview.py)

InterviewQuestionSet gồm danh sách InterviewQuestion. Mỗi câu hỏi có:
- question: nội dung câu hỏi, viết bằng tiếng Việt.
- category: loại câu hỏi, một trong 4 giá trị:
  - skill_gap: kỹ năng JD yêu cầu mà CV còn thiếu.
  - skill_verification: kiểm chứng kỹ năng CV chỉ đáp ứng gián tiếp.
  - experience: đào sâu kinh nghiệm dự án.
  - behavioral: hành vi, tình huống làm việc.
- target_skill: kỹ năng mà câu hỏi đánh giá.
- purpose: người phỏng vấn cần tìm hiểu điều gì.
- good_answer_hints: các ý mà một câu trả lời tốt cần có, để người phỏng vấn đối chiếu.

Giống CVExtraction, schema không có giá trị mặc định nên dùng được cho cả Gemini (response_schema) và Ollama (format).

## Service sinh câu hỏi (backend/app/services/interview_generator.py)

**Đầu vào lấy từ kết quả các bước trước, không gửi lại toàn văn CV.** Câu hỏi nhắm đúng lỗ hổng và tốn ít token hơn. Đầu vào gồm:
- JD: tiêu đề, yêu cầu, kỹ năng bắt buộc / ưu tiên, số năm kinh nghiệm tối thiểu.
- Hồ sơ do AI bóc tách (Mục 4.4): chức danh, tóm tắt, kỹ năng, tối đa 5 mục kinh nghiệm.
- Phân tích lỗ hổng (Mục 4.7):
  - Kỹ năng bắt buộc còn thiếu và kỹ năng ưu tiên còn thiếu.
  - Kỹ năng chỉ khớp gián tiếp (tầng semantic/text) cần kiểm chứng.
  - Ghi chú kinh nghiệm: thiếu số năm so với JD, hoặc số năm tự tính lệch với số CV ghi (cờ discrepancy ở Issues/05).
- Nếu bước bóc tách CV thất bại, dùng tạm 6.000 ký tự đầu của văn bản CV.

**System prompt:**
- Thứ tự ưu tiên câu hỏi: kỹ năng bắt buộc còn thiếu → kỹ năng cần kiểm chứng → kỹ năng ưu tiên còn thiếu → đào sâu kinh nghiệm → câu hỏi hành vi.
- Mỗi kỹ năng bắt buộc còn thiếu có ít nhất một câu hỏi.
- Với kỹ năng còn thiếu: hỏi năng lực tương đương hoặc khả năng học nhanh, gắn với kinh nghiệm ứng viên đã có. Không giả định ứng viên đã dùng kỹ năng đó.
- Câu hỏi mở, gắn tình huống thực tế. Không hỏi có/không, không hỏi định nghĩa sách vở.
- Cấm hỏi các nội dung phân biệt đối xử: tuổi, giới tính, hôn nhân, con cái, tôn giáo, dân tộc, quê quán, sức khỏe, chính trị.
- Có một ví dụ mẫu "không tốt / tốt" thuộc lĩnh vực khác (DevOps/Kubernetes), để mô hình học cách viết mà không sao chép nội dung.

**Gọi qua ai_provider:** dùng chung cơ chế AI_PROVIDER=cloud|local|auto và chuỗi model dự phòng của Mục 4.9 – 4.10.

**Hậu xử lý (normalize_interview_questions):**
- Chuẩn hóa khoảng trắng.
- Bỏ câu rỗng và câu trùng lặp (không phân biệt hoa thường, dấu câu).
- Giữ tối đa 5 câu. Ít hơn 3 câu thì ghi cảnh báo vào log.
- strip_yes_no_opener: bỏ vế mở đầu dạng có/không (VD "Bạn đã từng làm việc với FastAPI chưa? Hãy so sánh..." thành "Hãy so sánh..."). Giữ nguyên các câu "Bạn có thể chia sẻ... không?" và câu hỏi về hệ thống.

## Tích hợp tác vụ ngầm (backend/app/services/ai_tasks.py)

Đây là bước 7 của pipeline, chạy sau Hybrid Score:
- Application.interview_questions lưu danh sách nội dung câu hỏi (dạng chuỗi). API ai-analysis và bảng Kanban dùng trực tiếp, không phải đổi schema API.
- ai_extracted_info.interview_details = {questions: [chi tiết từng câu], ai_meta: {provider, model, latency_seconds, attempts}}. Modal chi tiết ứng viên (Mục 6) dùng để hiển thị mục đích và gợi ý đáp án.
- Lỗi AI được bắt và ghi log. Điểm số đã lưu ở các bước trước không bị ảnh hưởng.

## Kiểm thử

### Unit test

backend/tests/test_interview_generator.py có 16 bài test:
- Prompt chứa đủ JD, hồ sơ và lỗ hổng. Chỉ kỹ năng khớp gián tiếp được đưa vào danh sách cần kiểm chứng. Ghi chú kinh nghiệm đúng.
- Dùng văn bản CV khi không có hồ sơ bóc tách. Prompt có quy tắc chống phân biệt đối xử.
- Khử trùng lặp, giới hạn 5 câu, bỏ vế mở đầu có/không (6 trường hợp).
- Truyền đúng schema; ít câu thì chỉ cảnh báo; thiếu dữ liệu ứng viên thì báo lỗi; lỗi AI được báo lên tầng trên.
- Schema tương thích: không có giá trị mặc định, category là enum, google-genai chấp nhận.

Toàn bộ test suite: 184/184 tests passed (OK).

### So sánh chất lượng Gemini và qwen2.5:7b

CV3 – Lê Hoàng Phúc, thiếu FastAPI, SQLAlchemy, MySQL:

| | Gemini (gemini-3.8-flash) | qwen2.5:7b (Ollama) |
| --- | --- | --- |
| Thời gian | 20.6s | 15.8s |
| Gắn với hồ sơ | Rất tốt: Starlette/Pydantic → FastAPI, Oracle → MySQL InnoDB, dự án "giảm 35% độ trễ" | Trung bình |
| Gợi ý đáp án | Cụ thể (AsyncSession, joinedload/selectinload, EXPLAIN, clustered index) | Chung chung |
| Vấn đề | — | Mở đầu "Bạn đã từng... chưa?"; gộp nhiều kỹ năng vào một câu |

Quá trình cải thiện prompt cho qwen:
1. **Thêm ví dụ mẫu cùng lĩnh vực (Flask → FastAPI):** qwen chép gần nguyên văn ví dụ và bịa "Bạn đã xây dựng API bằng Flask" dù CV không có Flask. Đây là hiện tượng rò rỉ ví dụ (few-shot leakage).
2. **Đổi ví dụ sang lĩnh vực khác (Kubernetes) + quy tắc "chỉ nhắc kinh nghiệm có trong hồ sơ":** hết sao chép, nhưng vẫn mở đầu bằng câu có/không. Mô hình 7B khó tuân thủ các quy tắc phủ định.
3. **Thêm bước hậu xử lý strip_yes_no_opener:** loại vế có/không một cách chắc chắn bằng code, giữ lại câu hỏi mở phía sau.

Kết luận: Gemini là lựa chọn chính cho chất lượng câu hỏi. qwen2.5:7b dùng được ở vai trò dự phòng hoặc chạy offline.

### Kiểm thử End-to-End (AI_PROVIDER=auto, API thật, CSDL Aiven)

| CV | Matching | Câu hỏi | Model | Nội dung chính |
| --- | --- | --- | --- | --- |
| CV1 – Rất phù hợp | 89.33 ✅ | 5 | gemini-3.8-flash | Không thiếu kỹ năng nên đào sâu kinh nghiệm: quản lý async session FastAPI/SQLAlchemy ở dự án ATS TopCV, tối ưu truy vấn giảm 40%, cache invalidation Redis–MySQL, xử lý sự cố production |
| CV2 – Kế toán | 10.00 ✅ | 5 | gemini-3.5-flash (dự phòng sau 2 lần 503) | 4 câu skill_gap dựa trên nền tảng Excel/MISA (VD: viết script Python đọc hóa đơn Excel → JSON) + 1 câu khả năng tự học khi chuyển ngành |
| CV3 – Đồng nghĩa | 54.36 | 4 | gemini-3.8-flash | 3 câu skill_gap (FastAPI, SQLAlchemy, MySQL) gắn với Starlette/ORM/dự án 50.000 người dùng + 1 câu kiểm chứng Docker |

Không có lỗi nào. Chuỗi model dự phòng tự xử lý 4 lần lỗi 503 của gemini-3.8-flash và 3.7-flash trong lần chạy.

## Cập nhật Checklist

Đã đánh dấu [x] Mục 4.8. Mục 4 – AI Pipeline & Scoring Engine đã hoàn thành toàn bộ 10/10 mục.
