# SmartRecruit AI Development Checklist

Checklist này phản ánh kiến trúc và ngăn xếp công nghệ hiện tại của dự án **Hệ thống quản lý tuyển dụng thông minh kết hợp trí tuệ nhân tạo**:

* **Mô hình kiến trúc:** Client – Server Monolith (Decoupled)
* **Frontend:** HTML5, CSS3, JavaScript thuần (ES6+), Bootstrap 5 (CDN), SortableJS (Kanban Drag & Drop CDN)
* **Backend:** Python 3.10+, FastAPI, Uvicorn, SQLAlchemy, PyMySQL
* **Database:** MySQL 8.0 trên nền tảng Cloud Aiven
* **AI Engine:** Kiến trúc Hybrid (Local CPU Sentence-Transformers + Cloud Google Gemini API + Dự phòng Ollama trên GPU RTX 4060)
* **Quy mô nhân sự:** Nhóm 02 thành viên

Ký hiệu:

* `[x]` Đã hoàn thành
* `[~]` Đang thực hiện / Đã có nền tảng, cần hoàn thiện wiring hoặc nghiệp vụ
* `[ ]` Chưa thực hiện

---

## 1. Project Foundation & Environment Setup

* [x] Thống nhất đề tài, hoàn thiện Bản đề xuất dự án (Proposal) và Biên bản họp lần 1
* [x] Thống nhất phân chia phạm vi công việc 02 người (Frontend/Docs vs Backend/AI)
* [x] Khởi tạo Git repository và quy tắc phân nhánh (`main`, `dev`, `feature/*`)
* [x] Thiết lập cấu trúc thư mục dự án chuẩn (`/backend`, `/frontend`, `/docs`, `/uploads`)
* [x] Cấu hình môi trường Python ảo (`venv`) và xuất file `requirements.txt`
* [x] Khởi tạo instance MySQL 8.0 miễn phí trên Cloud Aiven
* [x] Tạo file `.env` chứa chuỗi kết nối Aiven MySQL, Gemini API Key và cờ cấu hình AI
* [x] Khởi tạo ứng dụng FastAPI cơ bản, kiểm tra trang tự sinh tài liệu `/docs` (Swagger UI)
* [x] Dựng trang Frontend tĩnh cơ bản kiểm tra tích hợp Bootstrap 5 và SortableJS qua CDN

## 2. Database & Data Access Layer (Aiven MySQL)

* [x] Cấu hình kết nối SQLAlchemy và `PyMySQL` với Aiven Cloud (hỗ trợ SSL)
* [x] Thiết kế và tạo model `User` (tài khoản quản trị/HR)
* [x] Thiết kế và tạo model `Job` (thông tin tin tuyển dụng, tiêu chí JD, kỹ năng yêu cầu)
* [x] Thiết kế và tạo model `Candidate` (hồ sơ ứng viên, thông tin liên hệ, link file CV)
* [x] Thiết kế và tạo model `Application` (liên kết Job - Candidate, trạng thái Kanban, Matching Score, JSON phân tích AI)
* [x] Cấu hình quan hệ (Foreign Keys, Relationships) giữa các bảng
* [x] Viết script tự động khởi tạo bảng (`Base.metadata.create_all`)
* [x] Viết script Seed dữ liệu mẫu (01 tài khoản HR, 02 tin tuyển dụng lập trình viên)
* [x] Kiểm tra kết nối và truy vấn CSDL đồng thời từ cả máy chính và máy phụ

## 3. Backend RESTful APIs (FastAPI)

* [x] Tạo module xác thực và đăng nhập cơ bản cho HR
* [x] Xây dựng nhóm API quản lý tin tuyển dụng (`/api/jobs`): tạo, sửa, đóng tin, xem chi tiết
* [x] Xây dựng API public cho ứng viên lấy danh sách việc làm đang mở
* [x] Xây dựng API tiếp nhận nộp hồ sơ (`/api/applications/apply` hỗ trợ multipart `UploadFile`)
* [x] Lưu trữ tệp PDF CV cục bộ an toàn trong thư mục `/uploads/cv`
* [x] Tích hợp `BackgroundTasks` của FastAPI để xử lý đọc và chấm điểm AI ngầm sau khi nộp
* [x] Xây dựng API lấy danh sách ứng viên theo từng Job kèm bộ lọc trạng thái và điểm số
* [x] Xây dựng API cập nhật trạng thái ứng viên khi kéo thả trên Kanban (`/api/applications/{id}/status`)
* [x] Xây dựng API lấy chi tiết phân tích AI (kỹ năng bóc tách, điểm số, gợi ý phỏng vấn)
* [x] Bổ sung cho frontend: trường `ai_status` (tiến trình AI) và API xem tệp CV gốc (`/api/applications/{id}/cv`)

## 4. AI Pipeline & Scoring Engine

* [x] Tạo service trích xuất văn bản thô từ file PDF bằng thư viện `pdfplumber`
* [x] Xử lý làm sạch chuỗi văn bản (loại bỏ ký tự đặc biệt, ngắt dòng thừa)
* [x] Tích hợp Google Gemini API (Flash model) với chế độ Structured Outputs
* [x] Xây dựng prompt chuẩn hóa thông tin CV trả về JSON (họ tên, kỹ năng, số năm kinh nghiệm, học vấn)
* [x] Tải và cấu hình mô hình nhúng `sentence-transformers` (`paraphrase-multilingual-MiniLM-L12-v2`)
* [x] Viết hàm tính độ tương đồng ngữ nghĩa Cosine Similarity giữa vector JD và vector CV
* [x] Cài đặt thuật toán Hybrid Matching Score: $40\% \text{ Hard Filter} + 60\% \text{ Semantic Match}$
* [x] Viết prompt cho Gemini sinh 3 – 5 câu hỏi phỏng vấn khai thác lỗ hổng kỹ năng của ứng viên
* [x] Tạo service adapter dự phòng gọi mô hình cục bộ `qwen2.5:7b` qua Ollama trên máy RTX 4060
* [x] Cơ chế chuyển đổi linh hoạt qua biến môi trường `AI_PROVIDER=cloud|local|auto`

## 5. Candidate Portal (Frontend)

* [x] Thiết kế giao diện trang chủ (`index.html`) hiển thị danh sách tin tuyển dụng
* [x] Thiết kế trang/modal xem chi tiết bản mô tả công việc (JD)
* [x] Xây dựng biểu mẫu (Form) nộp CV trực tuyến (Họ tên, Email, Số điện thoại, Tải file PDF)
* [x] Viết JavaScript kiểm tra định dạng tệp (chỉ nhận `.pdf`, `.docx`) và giới hạn dung lượng (< 5MB)
* [x] Kết nối hàm `fetch()` gửi `FormData` lên API nộp hồ sơ của Backend
* [x] Hiển thị thông báo trạng thái nộp hồ sơ (Loading spinner, thông báo thành công / lỗi)

## 6. HR ATS & Kanban Dashboard (Frontend)

* [x] Thiết kế giao diện bảng điều khiển nhân sự (`admin.html`) với thanh điều hướng Bootstrap 5
* [x] Xây dựng giao diện tạo tin tuyển dụng mới kèm ô nhập tiêu chí bắt buộc
* [x] Xây dựng bảng Kanban với 5 cột trạng thái: *Applied*, *Screening*, *Interview*, *Offer*, *Rejected* (chốt 17/10/2026, khớp 5 trạng thái backend)
* [x] Tích hợp thư viện `SortableJS` cho phép kéo thả các thẻ ứng viên qua lại giữa các cột
* [x] Thiết kế thẻ ứng viên (Candidate Card): Tên, vị trí, huy hiệu điểm Matching Score tô màu trực quan ($\ge 80\%$ xanh, $50-79\%$ vàng, $< 50\%$ đỏ)
* [x] Bắt sự kiện kéo thả thẻ (`onEnd`) để gọi API cập nhật trạng thái về Backend tức thì
* [x] Xây dựng Modal hiển thị hồ sơ chi tiết và bảng đánh giá của AI khi HR bấm vào ứng viên
* [x] Hiển thị danh sách kỹ năng trùng khớp, kỹ năng còn thiếu và các câu hỏi phỏng vấn gợi ý
* [x] Xây dựng trang quản lý tin tuyển dụng (mục "Tin tuyển dụng" trên thanh điều hướng): bảng tiêu đề, trạng thái, ngày đăng, số kỹ năng bắt buộc; nút Sửa / Đóng tin / Xem Kanban (bổ sung 17/10/2026, dùng API sẵn có)
* [x] Gộp nhánh `frontend-hai` vào `frontend-tan`: giữ JS của `frontend-tan`, áp giao diện (HTML/CSS, menu dọc) của Hải lên `index.html` và `admin.html` (bổ sung 23/10/2026)

## 7. Supporting Services & Notifications

* [x] Xây dựng Service gửi Email tự động qua SMTP (sử dụng tài khoản Gmail App Password) (xong 23/10/2026: `EMAIL_MODE=smtp|file|off`, mặc định `file` ghi `.eml`; chưa gửi thử Gmail thật vì chưa có App Password)
* [x] Mẫu email 1: Xác nhận đã nhận hồ sơ gửi tự động cho ứng viên
* [x] Mẫu email 2: Thư mời phỏng vấn tự động khi HR kéo ứng viên sang cột *Interview* (HR nhập giờ / địa điểm trong hộp xác nhận, bỏ trống thì thư báo sẽ liên hệ; tin tuyển dụng có thêm trường địa điểm)
* [x] Mẫu email 3: Thư thông báo kết quả (Offer Letter hoặc Thư cảm ơn từ chối)
* [x] Xây dựng bộ lọc danh sách ứng viên trên bảng Kanban theo điểm số từ cao xuống thấp (frontend xong 23/10/2026: ô *Sắp xếp* điểm cao → thấp / mới nộp trước, ô *Điểm tối thiểu* tất cả / từ 50 / từ 80)

## 8. Quality, Testing & Defense Preparation

* [x] Chuẩn bị bộ dữ liệu thử nghiệm gồm 03 hồ sơ CV mẫu:
* *CV 1:* Rất phù hợp với JD (kỳ vọng điểm $> 85\%$)
* *CV 2:* Trái ngành / Không liên quan (kỳ vọng điểm $< 40\%$)
* *CV 3:* Khác từ ngữ nhưng đồng nghĩa (kiểm tra tính năng Semantic Matching)


* [x] Kiểm thử toàn bộ luồng hoạt động từ phía Ứng viên nộp bài đến HR thao tác trên Kanban (xong 28/10/2026 với AI `auto` và `local`, email chế độ `file`; chưa gửi Gmail thật. Báo cáo: `docs/Test-Reports/2026-10-28_1711_toan-app-8.2.md`)
* [~] Kiểm thử hiệu năng và độ ổn định của API xử lý nền (`BackgroundTasks`) (10 hồ sơ nộp lần lượt ổn định, chưa test nhiều hồ sơ cùng lúc)
* [~] Kiểm thử chuyển đổi sang chạy mô hình Local Ollama trên GPU RTX 4060 ở trạng thái ngắt mạng (đã chạy `local`, chưa ngắt mạng)
* [ ] Tối ưu hóa mã nguồn Frontend, loại bỏ code thừa và chuẩn hóa thông báo lỗi giao diện
* [x] Soạn thảo tài liệu hướng dẫn cài đặt và chạy hệ thống trong file `README.md`
* [ ] Đóng gói tài liệu báo cáo đồ án, thiết kế slide thuyết trình và kịch bản demo bảo vệ

## 9. Việc tồn đọng sau kiểm thử thật

Chi tiết từng vấn đề: `docs/Issues/`. Lịch sử test: `docs/Test-Reports/`.

* [x] Chạy test Gemini đầy đủ hạn mức (`AI_PROVIDER=auto`) (đã chạy 28/10/2026 trong Mục 8.2: `docs/Test-Reports/2026-10-28_1711_backend-auto.md`)
* [x] Issue 04: Một số PDF bị đọc ra chữ dính liền, mất dấu cách (xong 28/10/2026: đọc lại trang với `x_tolerance=1.5`)
* [x] Issue 06: CV `.docx` được nhận nhưng AI chưa đọc được (chốt 28/10/2026: bỏ `.docx`, API và form chỉ nhận PDF)
* [x] Issue 07: Kinh nghiệm trái ngành vẫn được tính đủ điểm (chốt 28/10/2026: giữ nguyên công thức, ghi là hạn chế trong báo cáo)
* [x] Issue 08: qwen2.5:7b sinh câu hỏi phỏng vấn chất lượng thấp (xong 28/10/2026: prompt riêng cho Ollama, kiểm tra và sinh lại, ghi chú trên giao diện; bổ sung 30/10/2026: thêm câu hỏi mẫu khi còn dưới 3 câu)
* [x] Chốt cách hiển thị Kanban: 5 cột theo 5 trạng thái backend (`offer` và `rejected` tách riêng), chốt 17/10/2026
* [ ] Tải CA certificate Aiven và đặt `DB_SSL_CA` để bật xác minh chứng chỉ máy chủ
* [x] Viết tài liệu API cho frontend (`docs/API cho Frontend.md`)

---

## Project Architecture

Hệ thống được tổ chức trong một kho mã nguồn duy nhất, tách biệt rõ ràng giữa tầng hiển thị và tầng xử lý:

```text
ai-recruitment-system/
├── backend/
│   ├── app/
│   │   ├── api/          # Các router endpoints (jobs, candidates, applications)
│   │   ├── core/         # Cấu hình hệ thống, biến môi trường (.env)
│   │   ├── models/       # Định nghĩa bảng CSDL SQLAlchemy
│   │   ├── schemas/      # Pydantic schemas xác thực dữ liệu vào/ra
│   │   ├── services/     # Logic nghiệp vụ, AI Pipeline, Parser, Email
│   │   └── main.py       # Điểm khởi động ứng dụng FastAPI
│   ├── requirements.txt  # Danh sách thư viện Python
│   └── uploads/          # Thư mục lưu trữ tệp CV ứng viên tải lên
├── frontend/
│   ├── css/              # Tệp định dạng tùy chỉnh
│   ├── js/               # Logic JavaScript gọi API, xử lý SortableJS Kanban
│   ├── index.html        # Giao diện Cổng ứng viên xem việc và nộp CV
│   └── admin.html        # Giao diện Bảng Kanban quản trị tuyển dụng của HR
├── docs/                 # Bản đề xuất dự án, Biên bản họp nhóm, Báo cáo
├── CHECKLIST.md          # Bảng theo dõi tiến độ công việc
└── README.md             # Hướng dẫn thiết lập và khởi chạy dự án

```

---

## Current Milestone

**Cập nhật 17/10/2026:** Đã xong frontend Mục 5 (Cổng ứng viên) và Mục 6 (Bảng điều khiển HR, gồm 6.9 trang quản lý tin) trên nhánh `feature/frontend-tan`; nhật ký ở `docs/Phan 5/`, `docs/Phan 6/`. Cách chạy cả hệ thống: `README.md` mục 4–5. Việc tiếp theo phía frontend: 8.2 (kiểm thử trọn luồng), 8.5 (dọn code, chuẩn hóa thông báo lỗi).

**Cập nhật 16/10/2026:** Đã xong backend lõi (Mục 1–4): CSDL Aiven (TLS), REST API, AI Pipeline Hybrid (Gemini + Ollama dự phòng, Sentence-Transformers), chấm điểm và sinh câu hỏi phỏng vấn. Lần test toàn bộ backend gần nhất đạt hết (unit 184, smoke API 35/35, E2E). Giai đoạn tiếp theo: frontend (Mục 5, 6) theo `docs/API cho Frontend.md`; song song backend làm Mục 7 (email) và các việc ở Mục 9.
