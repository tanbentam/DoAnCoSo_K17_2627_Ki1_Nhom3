Các nội dung đã hoàn thành:

Xây dựng module so khớp ngữ nghĩa backend/app/services/semantic_matching.py:

cosine_similarity(a, b): Cài đặt công thức cos(θ) = (a · b) / (‖a‖ · ‖b‖) bằng NumPy, không yêu cầu vector đã chuẩn hóa, vector 0 trả về 0.0, kiểm tra khớp số chiều, giới hạn kết quả trong [-1, 1] để loại sai số dấu phẩy động.
cosine_similarity_matrix(A, B): Tính ma trận cosine nhiều-nhiều (n × m) một lần bằng phép nhân ma trận, chuẩn bị cho so khớp danh sách kỹ năng JD × CV ở Mục 4.7.
similarity_to_score: Hiệu chỉnh tuyến tính cosine về thang điểm 0–100: cosine ≤ SEMANTIC_SIM_FLOOR (0.20) → 0 điểm, cosine ≥ SEMANTIC_SIM_CEIL (0.80) → 100 điểm.
build_job_text: Ghép tiêu đề, mô tả, yêu cầu, kỹ năng bắt buộc và kỹ năng ưu tiên của tin tuyển dụng thành văn bản JD để nhúng vector.
compute_semantic_match / compute_job_cv_match: Nhúng JD và CV thành vector 384 chiều (encode_document - Mục 4.5), tính cosine và trả về SemanticMatchResult(similarity, score).

Hiệu chỉnh thang điểm dựa trên đo đạc thực tế:

Với mô hình paraphrase-multilingual-MiniLM-L12-v2, hai văn bản hồ sơ bất kỳ hiếm khi có cosine < 0.2 nên nếu lấy cosine × 100, CV trái ngành vẫn được ~22 điểm và CV rất khớp chỉ ~79 điểm. Đo trên JD "Backend Developer (Python/FastAPI)":

| CV | Cosine thô | Semantic score |
| --- | --- | --- |
| Backend Python/FastAPI khớp JD | 0.790 | ~98 |
| Diễn đạt khác từ ngữ nhưng đồng nghĩa | 0.555 | ~59 |
| Frontend VueJS (khác vị trí) | 0.321 | ~20 |
| Kế toán (trái ngành) | 0.219 | ~3 |

Hai ngưỡng có thể chỉnh trong .env (SEMANTIC_SIM_FLOOR, SEMANTIC_SIM_CEIL) khi kiểm thử với bộ CV mẫu ở Mục 8.

Tích hợp đồng bộ vào hệ thống:

Tác vụ ngầm backend/app/services/ai_tasks.py: sau bước Gemini bóc tách CV, tính semantic match giữa JD của tin tuyển dụng và văn bản CV, lưu điểm vào Application.semantic_score (trọng số 60% của Hybrid Matching Score ở Mục 4.7). Lỗi mô hình nhúng được bắt và ghi log, không làm hỏng tác vụ ngầm.
Cấu hình: bổ sung SEMANTIC_SIM_FLOOR, SEMANTIC_SIM_CEIL trong config.py và .env.example.
Package Init: Xuất khẩu các hàm semantic_matching trong backend/app/services/__init__.py.

Kiểm thử:

Unit test backend/tests/test_semantic_matching.py (19 bài test): vector giống hệt, bất biến theo độ dài, trực giao/ngược chiều, giá trị tính tay 2/√5, vector 0, sai số chiều, ma trận nhiều-nhiều khớp từng cặp, hiệu chỉnh điểm và giới hạn, ghép văn bản JD, luồng so khớp với encoder giả lập; 1 bài test với mô hình thật kiểm tra thứ hạng CV khớp > CV đồng nghĩa > CV trái ngành (tự bỏ qua nếu chưa tải mô hình).
Chạy toàn bộ test suite dự án: 75/75 tests passed (OK).

Cập nhật Checklist:

Đã đánh dấu [x] hoàn thành mục này trong checklist.md.
