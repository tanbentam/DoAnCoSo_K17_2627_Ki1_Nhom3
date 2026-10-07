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
* [ ] Khởi tạo instance MySQL 8.0 miễn phí trên Cloud Aiven
* [ ] Tạo file `.env` chứa chuỗi kết nối Aiven MySQL, Gemini API Key và cờ cấu hình AI
* [x] Khởi tạo ứng dụng FastAPI cơ bản, kiểm tra trang tự sinh tài liệu `/docs` (Swagger UI)
* [x] Dựng trang Frontend tĩnh cơ bản kiểm tra tích hợp Bootstrap 5 và SortableJS qua CDN

## 2. Database & Data Access Layer (Aiven MySQL)

* [ ] Cấu hình kết nối SQLAlchemy và `PyMySQL` với Aiven Cloud (hỗ trợ SSL)
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
* [ ] Xây dựng API public cho ứng viên lấy danh sách việc làm đang mở
* [ ] Xây dựng API tiếp nhận nộp hồ sơ (`/api/applications/apply` hỗ trợ multipart `UploadFile`)
* [ ] Lưu trữ tệp PDF CV cục bộ an toàn trong thư mục `/uploads/cv`
* [ ] Tích hợp `BackgroundTasks` của FastAPI để xử lý đọc và chấm điểm AI ngầm sau khi nộp
* [ ] Xây dựng API lấy danh sách ứng viên theo từng Job kèm bộ lọc trạng thái và điểm số
* [ ] Xây dựng API cập nhật trạng thái ứng viên khi kéo thả trên Kanban (`/api/applications/{id}/status`)
* [ ] Xây dựng API lấy chi tiết phân tích AI (kỹ năng bóc tách, điểm số, gợi ý phỏng vấn)

## 4. AI Pipeline & Scoring Engine

* [ ] Tạo service trích xuất văn bản thô từ file PDF bằng thư viện `pdfplumber`
* [ ] Xử lý làm sạch chuỗi văn bản (loại bỏ ký tự đặc biệt, ngắt dòng thừa)
* [ ] Tích hợp Google Gemini API (Flash model) với chế độ Structured Outputs
* [ ] Xây dựng prompt chuẩn hóa thông tin CV trả về JSON (họ tên, kỹ năng, số năm kinh nghiệm, học vấn)
* [ ] Tải và cấu hình mô hình nhúng `sentence-transformers` (`paraphrase-multilingual-MiniLM-L12-v2`)
* [ ] Viết hàm tính độ tương đồng ngữ nghĩa Cosine Similarity giữa vector JD và vector CV
* [ ] Cài đặt thuật toán Hybrid Matching Score: $40\% \text{ Hard Filter} + 60\% \text{ Semantic Match}$
* [ ] Viết prompt cho Gemini sinh 3 – 5 câu hỏi phỏng vấn khai thác lỗ hổng kỹ năng của ứng viên
* [ ] Tạo service adapter dự phòng gọi mô hình cục bộ `qwen2.5:7b` qua Ollama trên máy RTX 4060
* [ ] Cơ chế chuyển đổi linh hoạt qua biến môi trường `AI_PROVIDER=cloud|local`

## 5. Candidate Portal (Frontend)

* [ ] Thiết kế giao diện trang chủ (`index.html`) hiển thị danh sách tin tuyển dụng
* [ ] Thiết kế trang/modal xem chi tiết bản mô tả công việc (JD)
* [ ] Xây dựng biểu mẫu (Form) nộp CV trực tuyến (Họ tên, Email, Số điện thoại, Tải file PDF)
* [ ] Viết JavaScript kiểm tra định dạng tệp (chỉ nhận `.pdf`, `.docx`) và giới hạn dung lượng (< 5MB)
* [ ] Kết nối hàm `fetch()` gửi `FormData` lên API nộp hồ sơ của Backend
* [ ] Hiển thị thông báo trạng thái nộp hồ sơ (Loading spinner, thông báo thành công / lỗi)

## 6. HR ATS & Kanban Dashboard (Frontend)

* [ ] Thiết kế giao diện bảng điều khiển nhân sự (`admin.html`) với thanh điều hướng Bootstrap 5
* [ ] Xây dựng giao diện tạo tin tuyển dụng mới kèm ô nhập tiêu chí bắt buộc
* [ ] Xây dựng bảng Kanban với 4 cột trạng thái: *Applied*, *Screening*, *Interview*, *Offer/Reject*
* [ ] Tích hợp thư viện `SortableJS` cho phép kéo thả các thẻ ứng viên qua lại giữa các cột
* [ ] Thiết kế thẻ ứng viên (Candidate Card): Tên, vị trí, huy hiệu điểm Matching Score tô màu trực quan ($\ge 80\%$ xanh, $50-79\%$ vàng, $< 50\%$ đỏ)
* [ ] Bắt sự kiện kéo thả thẻ (`onEnd`) để gọi API cập nhật trạng thái về Backend tức thì
* [ ] Xây dựng Modal hiển thị hồ sơ chi tiết và bảng đánh giá của AI khi HR bấm vào ứng viên
* [ ] Hiển thị danh sách kỹ năng trùng khớp, kỹ năng còn thiếu và các câu hỏi phỏng vấn gợi ý

## 7. Supporting Services & Notifications

* [ ] Xây dựng Service gửi Email tự động qua SMTP (sử dụng tài khoản Gmail App Password)
* [ ] Mẫu email 1: Xác nhận đã nhận hồ sơ gửi tự động cho ứng viên
* [ ] Mẫu email 2: Thư mời phỏng vấn tự động khi HR kéo ứng viên sang cột *Interview*
* [ ] Mẫu email 3: Thư thông báo kết quả (Offer Letter hoặc Thư cảm ơn từ chối)
* [ ] Xây dựng bộ lọc danh sách ứng viên trên bảng Kanban theo điểm số từ cao xuống thấp

## 8. Quality, Testing & Defense Preparation

* [ ] Chuẩn bị bộ dữ liệu thử nghiệm gồm 03 hồ sơ CV mẫu:
* *CV 1:* Rất phù hợp với JD (kỳ vọng điểm $> 85\%$)
* *CV 2:* Trái ngành / Không liên quan (kỳ vọng điểm $< 40\%$)
* *CV 3:* Khác từ ngữ nhưng đồng nghĩa (kiểm tra tính năng Semantic Matching)


* [ ] Kiểm thử toàn bộ luồng hoạt động từ phía Ứng viên nộp bài đến HR thao tác trên Kanban
* [ ] Kiểm thử hiệu năng và độ ổn định của API xử lý nền (`BackgroundTasks`)
* [ ] Kiểm thử chuyển đổi sang chạy mô hình Local Ollama trên GPU RTX 4060 ở trạng thái ngắt mạng
* [ ] Tối ưu hóa mã nguồn Frontend, loại bỏ code thừa và chuẩn hóa thông báo lỗi giao diện
* [ ] Soạn thảo tài liệu hướng dẫn cài đặt và chạy hệ thống trong file `README.md`
* [ ] Đóng gói tài liệu báo cáo đồ án, thiết kế slide thuyết trình và kịch bản demo bảo vệ

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

Dự án đã hoàn thành giai đoạn khởi động (Milestone 1.1): thống nhất tên đề tài, chốt phạm vi nghiệp vụ cho nhóm 02 thành viên, phê duyệt kiến trúc Hybrid AI và phân công nhiệm vụ cụ thể. Giai đoạn tiếp theo tập trung vào việc thiết lập kết nối cơ sở dữ liệu Aiven MySQL, viết khung API FastAPI và xây dựng module bóc tách CV kết hợp thuật toán tính điểm Cosine Similarity.