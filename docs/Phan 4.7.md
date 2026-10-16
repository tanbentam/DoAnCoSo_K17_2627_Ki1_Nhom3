Các nội dung đã hoàn thành:

Xây dựng module chấm điểm backend/app/services/hybrid_scoring.py:

Công thức tổng: matching_score = 0.4 × hard_filter_score + 0.6 × semantic_score (trọng số cấu hình qua HYBRID_HARD_FILTER_WEIGHT, HYBRID_SEMANTIC_WEIGHT). Nếu thiếu một thành phần (VD: mô hình nhúng lỗi) thì dùng thành phần còn lại thay vì bỏ trống điểm.

Hard Filter (0–100) gồm 3 tiêu chí cứng của JD:
- 60% Kỹ năng bắt buộc (required_skills): tỷ lệ kỹ năng JD tìm thấy ở ứng viên.
- 25% Kinh nghiệm (experience_years_min): min(số năm ứng viên / số năm yêu cầu, 1); JD không yêu cầu → 100.
- 15% Kỹ năng ưu tiên (preferred_skills).
Tiêu chí không áp dụng được (JD không có kỹ năng ưu tiên, Gemini không xác định được số năm kinh nghiệm) được loại ra và chia lại trọng số cho các tiêu chí còn lại, tránh trừ điểm oan.

So khớp kỹ năng 4 tầng (từ chặt đến lỏng):
1. exact — trùng sau chuẩn hóa cách viết: "ReactJS" = "React.js" = "react", "HTML5" = "HTML", "Vue 3" = "VueJS", "Python 3.10" = "Python"; giữ nguyên tên ngắn như C#, C++, ES6.
2. alias — từ điển đồng nghĩa: Golang = Go, k8s = Kubernetes, Postgres = PostgreSQL, JS = JavaScript, RESTful API = REST API, Làm việc nhóm = Teamwork...
3. text — tên kỹ năng xuất hiện nguyên văn trong văn bản CV (bắt kỹ năng Gemini bỏ sót), kiểm tra đúng ranh giới từ để "SQL" không khớp nhầm "MySQL", "Java" không khớp "JavaScript".
4. semantic — cosine giữa vector tên kỹ năng ≥ 0.80 (SKILL_SEMANTIC_THRESHOLD), dùng cosine_similarity_matrix của Mục 4.6.

Đo đạc để chọn ngưỡng và quy tắc so khớp ngữ nghĩa (mô hình MiniLM-L12-v2):

| Cặp kỹ năng | Cosine | Kết quả |
| --- | --- | --- |
| Tiếng Anh ~ English | 0.971 | Khớp |
| MySQL ~ Cơ sở dữ liệu MySQL | 0.899 | Khớp |
| Redis ~ Redis Cache | 0.850 | Khớp |
| SQLAlchemy ~ SQL | 0.850 | Loại (quy tắc khái niệm rộng) |
| MySQL ~ SQL Server | 0.702 | Loại |
| VueJS ~ Vue 3 | 0.635 | Khớp ở tầng exact |
| Java ~ JavaScript | 0.441 | Loại |

Không thể chỉ dùng embedding vì "VueJS ~ Vue 3" (cùng kỹ năng) có cosine thấp hơn "MySQL ~ SQL Server" (khác sản phẩm), nên chuẩn hóa và từ điển alias được ưu tiên trước. Bổ sung quy tắc: kỹ năng ứng viên là khái niệm rộng hơn nằm trong tên kỹ năng JD (CV "SQL" so với JD "SQLAlchemy") không được tính, còn chiều ngược lại hợp lệ (CV "Redis Cache" đáp ứng JD "Redis").

Kết quả thử nghiệm toàn pipeline trên JD "Backend Developer (Python/FastAPI)" (mô hình nhúng thật):

| CV | Hard Filter | Semantic | Matching Score |
| --- | --- | --- | --- |
| CV 1: Backend Python/FastAPI rất phù hợp | 100 | 100 | 100 (kỳ vọng > 85) |
| CV 3: Diễn đạt khác từ ngữ, đồng nghĩa | 55 | 68.4 | 63.1 |
| Frontend VueJS (khác vị trí) | 25 | 17.0 | 20.2 |
| CV 2: Kế toán trái ngành | 25 | 0 | 10 (kỳ vọng < 40) |

Tích hợp đồng bộ vào hệ thống:

Tác vụ ngầm backend/app/services/ai_tasks.py: sau bước semantic match, tính Hybrid Score và lưu hard_filter_score, matching_score, matched_skills (kỹ năng JD đáp ứng), missing_skills (kỹ năng bắt buộc còn thiếu - đầu vào sinh câu hỏi phỏng vấn ở Mục 4.8) vào bảng applications. Chi tiết chấm điểm (điểm từng tiêu chí, kiểu khớp của từng kỹ năng, kỹ năng ưu tiên còn thiếu) được lưu tại ai_extracted_info.scoring_details để giao diện HR (Mục 6) hiển thị giải thích điểm.
Nếu Gemini lỗi (không có thông tin bóc tách) vẫn chấm được điểm bằng cách tìm kỹ năng trong văn bản CV thô.
Cấu hình: bổ sung HYBRID_HARD_FILTER_WEIGHT=0.4, HYBRID_SEMANTIC_WEIGHT=0.6, SKILL_SEMANTIC_THRESHOLD=0.80 trong config.py và .env.example.
Package Init: Xuất khẩu các hàm hybrid_scoring trong backend/app/services/__init__.py.

Kiểm thử:

Unit test backend/tests/test_hybrid_scoring.py (27 bài test): chuẩn hóa tên kỹ năng (biến thể cách viết, số phiên bản, tên ngắn, alias, không gộp nhầm), so khớp 4 tầng (exact/alias/text/semantic, ranh giới từ, quy tắc khái niệm rộng, dưới ngưỡng, lỗi mô hình), điểm kinh nghiệm, Hard Filter có trọng số và chia lại trọng số, công thức 40/60 và trường hợp thiếu thành phần; 3 bài test với mô hình thật theo kịch bản bảo vệ (CV phù hợp > 85, CV trái ngành < 40, "SQL" không đáp ứng "SQLAlchemy").
Chạy toàn bộ test suite dự án: 102/102 tests passed (OK).

Cập nhật Checklist:

Đã đánh dấu [x] hoàn thành mục này trong checklist.md.
