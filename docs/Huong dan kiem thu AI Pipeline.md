# Hướng dẫn kiểm thử luồng AI (Nộp CV → Chấm điểm)

Kiểm thử thật toàn bộ luồng: ứng viên nộp CV → tác vụ ngầm đọc PDF, làm sạch, Gemini bóc tách, so khớp ngữ nghĩa, tính Hybrid Score → HR xem kết quả. Dữ liệu được ghi vào CSDL Aiven thật.

## 0. Chuẩn bị (một lần)

Mở terminal tại thư mục `backend/`:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe download_embedding_model.py      # tải mô hình nhúng (~460MB)
.\venv\Scripts\python.exe -m pip install fpdf2              # chỉ để tạo CV mẫu
.\venv\Scripts\python.exe scripts\generate_sample_cvs.py    # tạo 3 CV mẫu Mục 8.1
```

3 CV mẫu nằm ở `backend/tests/fixtures/sample_cvs/`:

| Tệp | Kịch bản | Kỳ vọng (Job 1 – Backend Python/FastAPI) |
| --- | --- | --- |
| CV1_phu_hop_backend_python.pdf | Rất phù hợp JD | Matching Score > 85 |
| CV2_trai_nganh_ke_toan.pdf | Trái ngành (kế toán) | Matching Score < 40 |
| CV3_dong_nghia_server_side.pdf | Khác từ ngữ nhưng đồng nghĩa | Điểm trung bình, Semantic nhận ra liên quan |

## 1. Khởi động server (cửa sổ terminal 1)

```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app
```

Đợi khoảng 15 giây rồi mở http://127.0.0.1:8000/health, thấy `"embedding_model_loaded": true` là sẵn sàng. Log của từng bước AI (`[BackgroundTasks]`, `[GeminiService]`...) hiện ngay trong cửa sổ này.

## 2. Cách A — Chạy script tự động (cửa sổ terminal 2)

```powershell
.\venv\Scripts\python.exe scripts\e2e_test_pipeline.py --only-samples   # chỉ 3 CV mẫu (3 lượt gọi Gemini)
.\venv\Scripts\python.exe scripts\e2e_test_pipeline.py                  # 3 CV mẫu + CV thật trong uploads/cv (10 lượt)
.\venv\Scripts\python.exe scripts\e2e_test_pipeline.py --cleanup        # xóa toàn bộ dữ liệu test
```

Script tự đăng nhập HR, nộp từng CV, chờ chấm điểm xong rồi in điểm, kỹ năng khớp/thiếu, tóm tắt của Gemini và đánh giá đạt/chưa đạt kỳ vọng.

## 3. Cách B — Thao tác tay trên Swagger UI

Mở http://127.0.0.1:8000/docs

1. **Nộp CV:** `POST /api/applications/apply` → *Try it out* → nhập `job_id = 1`, họ tên, email (mỗi lần một email mới, VD `test.toi1@example.com`), chọn tệp PDF → *Execute*. Ghi lại `application_id` trả về.
2. **Đăng nhập HR:** bấm nút **Authorize** (góc phải trên) → username `hr@smartrecruit.com`, password `admin123` → *Authorize*.
3. **Xem kết quả AI:** đợi 15–60 giây (theo dõi log ở terminal 1 đến dòng `Hoàn tất chấm điểm AI`), gọi `GET /api/applications/{application_id}/ai-analysis`.

Các trường cần kiểm tra trong kết quả:

- `matching_score`, `hard_filter_score`, `semantic_score` — điểm tổng và điểm thành phần.
- `matched_skills`, `missing_skills` — kỹ năng JD đáp ứng / còn thiếu.
- `ai_extracted_info` — thông tin Gemini bóc tách (họ tên, kỹ năng, số năm kinh nghiệm, học vấn).
- `ai_extracted_info.scoring_details` — giải thích điểm: điểm từng tiêu chí và kiểu khớp của từng kỹ năng (exact / alias / text / semantic).

Email test nên có dạng `test.<tên>@example.com` để lệnh `--cleanup` xóa được.

## 4. Lưu ý về giới hạn Gemini miễn phí

Gói miễn phí của `gemini-3.8-flash` chỉ cho **20 lượt gọi mỗi ngày**. Khi hết, log hiện `429 RESOURCE_EXHAUSTED ... limit: 20` và hồ sơ vẫn được chấm điểm nhưng không có thông tin Gemini bóc tách (`ai_extracted_info` chỉ có `scoring_details`, kỹ năng được tìm trực tiếp trong văn bản CV). Hãy để dành lượt gọi cho buổi demo.
