# SmartRecruit AI 🚀
> **Hệ thống Quản lý Tuyển dụng Thông minh Kết hợp Trí tuệ Nhân tạo**  
> *Đồ án Cơ sở — Khoa Công nghệ Thông tin*

---

## 📖 1. Giới thiệu Dự án

**SmartRecruit AI** là một hệ thống ATS (Applicant Tracking System) hiện đại được thiết kế để giải quyết bài toán sàng lọc hồ sơ ứng viên tự động. Hệ thống hỗ trợ:
- **Cổng thông tin Ứng viên (Candidate Portal):** Xem việc làm đang mở, tìm kiếm, xem chi tiết JD, nộp hồ sơ trực tuyến đính kèm file CV (hiện chỉ nhận **PDF**, < 5MB — xem [Issue 06](docs/Issues/06-cv-docx-khong-duoc-cham.md)).
- **Cổng quản trị Nhân sự (HR Dashboard):** Đăng nhập; tạo / sửa / đóng tin tuyển dụng; bảng Kanban 5 cột kéo thả (SortableJS) với thẻ ứng viên tô màu theo điểm; modal hồ sơ chi tiết gồm đánh giá AI, kỹ năng khớp / thiếu, câu hỏi phỏng vấn gợi ý và CV gốc; trang quản lý tin tuyển dụng.
- **Công cụ Đánh giá AI (AI Engine):** Trích xuất văn bản từ CV, bóc tách thông tin bằng LLM (Google Gemini, dự phòng Ollama), tính điểm Hybrid (40% lọc cứng + 60% tương đồng ngữ nghĩa bằng Sentence-Transformers) và sinh câu hỏi phỏng vấn.

---

## 🛠️ 2. Ngăn xếp Công nghệ (Tech Stack)

| Thành phần | Công nghệ sử dụng |
|---|---|
| **Kiến trúc** | Client – Server Monolith (Decoupled) |
| **Backend** | Python 3.10+, FastAPI, Uvicorn, Pydantic |
| **Database & ORM** | MySQL 8.0 (Cloud Aiven), SQLAlchemy 2.0, PyMySQL (SSL) |
| **Authentication** | JWT (JSON Web Token), SHA-256 Hashing |
| **Frontend** | HTML5, CSS3, JavaScript thuần (ES6+), không có bước build. Qua CDN: Bootstrap 5 (`index.html`), Tabler (`admin.html`), Bootstrap Icons, SortableJS. Giao diện thống nhất theo thiết kế của nhánh `frontend-hai` |
| **AI Pipeline** | Google Gemini API (Flash Model) + Sentence-Transformers / Ollama Fallback |

---

## 📂 3. Cấu trúc Thư mục

```text
DoAnCoSo/
├── backend/
│   ├── app/
│   │   ├── api/            # API Routers (auth, jobs, applications)
│   │   ├── core/           # Cấu hình config, database connection, bảo mật
│   │   ├── models/         # Định nghĩa các SQLAlchemy ORM Models
│   │   ├── schemas/        # Pydantic DTO Schemas kiểm tra dữ liệu
│   │   ├── services/       # Logic nghiệp vụ, AI Pipeline, Parser
│   │   └── main.py         # Điểm khởi chạy ứng dụng FastAPI
│   ├── uploads/cv/         # Lưu trữ tệp PDF CV ứng viên an toàn
│   ├── init_db.py          # Script tự động tạo bảng CSDL
│   ├── seed_db.py          # Script nạp dữ liệu mẫu ban đầu
│   ├── requirements.txt    # Danh sách thư viện Python
│   └── venv/               # Môi trường ảo Python
├── frontend/
│   ├── css/
│   │   ├── style.css       # Giao diện chung (màu, nút, form, đăng nhập, Kanban, modal)
│   │   ├── menu/menu.css   # Menu dọc dùng chung cho ứng viên và HR
│   │   └── user/candidate-home.css  # Riêng cho Cổng ứng viên
│   ├── js/
│   │   ├── utils.js        # Hàm dùng chung: escapeHtml, formatDate, showToast, renderState…
│   │   ├── api.js          # API Client dùng chung (mọi lời gọi API đi qua đây)
│   │   ├── index.js        # Script cho Cổng Ứng viên
│   │   └── admin.js        # Script cho Bảng điều khiển HR (Kanban, tin tuyển dụng, hồ sơ)
│   ├── index.html          # Giao diện Cổng Ứng viên
│   └── admin.html          # Giao diện Bảng điều khiển Tuyển dụng (HR)
├── docs/                   # Hướng dẫn, tài liệu API, log từng mục (Phan N/), Issues, Test-Reports
├── .env                    # Biến môi trường bí mật (chứa connection string, API key)
├── .env.example            # Bản mẫu cấu hình môi trường
├── checklist.md            # Bảng theo dõi tiến độ chi tiết của dự án
└── README.md               # Tài liệu hướng dẫn dự án
```

---

## ⚙️ 4. Hướng dẫn Cài đặt & Thiết lập Môi trường

### 4.1. Chuẩn bị Môi trường
- Đã cài đặt **Python 3.10+** (khuyến nghị Python 3.12).
- Trình duyệt hiện đại (Chrome, Edge, Firefox). Máy cần có mạng để tải thư viện giao diện qua CDN.
- (Tùy chọn) **Ollama** với model `qwen2.5:7b` để chạy AI cục bộ khi không dùng Gemini.

> Các lệnh dưới đây viết cho **Windows PowerShell**. Python trong môi trường ảo nằm ở `venv\Scripts\python.exe` (trên macOS / Linux là `venv/bin/python`).

### 4.2. Thiết lập Biến Môi trường (.env)
Sao chép `.env.example` thành `.env` ở **thư mục gốc dự án** rồi điền giá trị thật (nhận từ người phụ trách backend qua kênh riêng, **không commit `.env`**). Các biến quan trọng:

| Biến | Ý nghĩa |
|---|---|
| `DATABASE_URL` | Chuỗi kết nối Aiven MySQL dạng `mysql+pymysql://user:pass@host:port/defaultdb`. **Không** thêm `?ssl_disabled=...`; SSL chỉnh bằng `DB_SSL_MODE` |
| `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_FALLBACK_MODELS` | Khóa và model Gemini (model dự phòng dùng khi hết hạn mức) |
| `AI_PROVIDER` | `cloud` (chỉ Gemini), `local` (chỉ Ollama), `auto` (Gemini, lỗi thì chuyển Ollama). Không có Ollama thì đặt `cloud` |
| `SECRET_KEY` | Chuỗi ngẫu nhiên để ký token đăng nhập |

Danh sách đầy đủ và giải thích từng biến: xem chú thích trong `.env.example`.

### 4.3. Cài đặt Thư viện Python
Mở Terminal tại thư mục `backend/`, tạo môi trường ảo (chỉ lần đầu) rồi cài thư viện:
```powershell
cd D:\3\DoAnCoSo\backend
python -m venv venv                      # chỉ chạy lần đầu, nếu chưa có thư mục venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Tải trước mô hình nhúng `paraphrase-multilingual-MiniLM-L12-v2` (~460MB, chỉ cần chạy 1 lần khi có mạng, sau đó dùng được offline):
```powershell
.\venv\Scripts\python.exe download_embedding_model.py
```

### 4.4. Khởi tạo Cơ sở Dữ liệu & Nạp Dữ liệu Mẫu
Chạy 2 script sau để đồng bộ bảng lên Cloud Aiven MySQL và tạo dữ liệu ban đầu:

```powershell
# 1. Tạo cấu trúc các bảng CSDL
.\venv\Scripts\python.exe init_db.py

# 2. Seed dữ liệu mẫu (1 HR, 2 tin tuyển dụng lập trình viên)
.\venv\Scripts\python.exe seed_db.py

# 3. Cập nhật cấu trúc bảng đã có (thêm cột mới). Chạy lại nhiều lần an toàn
.\venv\Scripts\python.exe migrate_db.py
```

> **Tài khoản HR mặc định sau khi seed:**
> - **Email:** `hr@smartrecruit.com`
> - **Mật khẩu:** `admin123`

---

## 🚀 5. Hướng dẫn Khởi chạy Hệ thống

### 5.1. Chạy Backend (FastAPI Server)
Mở Terminal và gõ:
```powershell
cd D:\3\DoAnCoSo\backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

- **Swagger UI (Tài liệu API tương tác):** 👉 [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Kiểm tra trạng thái (Health Check):** 👉 [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

Đợi dòng `Application startup complete`, mở `/health` thấy `"status": "healthy"` là backend sẵn sàng.

### 5.2. Chạy Frontend
Frontend là các file tĩnh, không cần cài thêm gì. Nên phục vụ qua một web server nhỏ (thay vì mở file trực tiếp) để đăng nhập, xem CV và tải lại trang ổn định. Mở **terminal thứ hai** tại thư mục gốc dự án:
```powershell
cd D:\3\DoAnCoSo
python -m http.server 5500 --bind 127.0.0.1 --directory frontend
```
- **Cổng Ứng viên:** 👉 [http://127.0.0.1:5500/index.html](http://127.0.0.1:5500/index.html)
- **Bảng điều khiển HR:** 👉 [http://127.0.0.1:5500/admin.html](http://127.0.0.1:5500/admin.html) (tài khoản ở mục 4.4)
- Cách khác: extension **Live Server** của VS Code (chuột phải `frontend/index.html` → *Open with Live Server*).
- Frontend gọi backend ở `http://127.0.0.1:8000` (hằng `API_BASE` ở đầu `frontend/js/api.js`). Backend chạy ở địa chỉ khác thì sửa hằng này.
- Hướng dẫn phát triển frontend: [docs/Huong dan phat trien Frontend.md](docs/Huong%20dan%20phat%20trien%20Frontend.md); chi tiết API: [docs/API cho Frontend.md](docs/API%20cho%20Frontend.md)

### 5.3. Dùng thử nhanh (luồng demo)
1. **Ứng viên:** mở `index.html` → chọn một tin → *Ứng tuyển* → điền họ tên, email, số điện thoại, chọn CV PDF → *Gửi hồ sơ*. CV mẫu có sẵn trong `backend/tests/fixtures/sample_cvs/` (nếu chưa có: `.\venv\Scripts\python.exe scripts\generate_sample_cvs.py` tại `backend/`).
2. **HR:** mở `admin.html` → đăng nhập → chọn đúng tin ở ô chọn tin. Thẻ ứng viên hiện "Đang chấm", **tự đổi sang điểm** sau khoảng 30–40 giây (xanh ≥ 80, vàng 50–79, đỏ < 50).
3. Kéo thẻ sang cột khác (hoặc dùng menu ⋮ trên thẻ): trạng thái được lưu ngay về backend.
4. Bấm vào thẻ: xem điểm, kỹ năng khớp / thiếu, kinh nghiệm, câu hỏi phỏng vấn gợi ý và CV gốc.
5. Mục **Tin tuyển dụng** trên thanh điều hướng: tạo / sửa / đóng tin, xem số hồ sơ từng tin.

> **CSDL dùng chung (Aiven):** khi thử, dùng email `test.<tên>@example.com` và tin tuyển dụng có tiêu đề bắt đầu bằng `[TEST]`. Dọn dữ liệu thử tại `backend/`: `.\venv\Scripts\python.exe scripts\e2e_test_pipeline.py --cleanup`.

### 5.4. Xử lý sự cố thường gặp
| Hiện tượng | Cách xử lý |
|---|---|
| Trang báo "Không kết nối được máy chủ" | Backend chưa chạy, hoặc chạy ở địa chỉ khác `API_BASE`. Kiểm tra http://127.0.0.1:8000/health |
| Giao diện vỡ, không có biểu tượng / font | Máy không có mạng để tải thư viện qua CDN |
| Sửa code frontend mà trình duyệt vẫn chạy bản cũ | Tải lại bằng **Ctrl + F5** để bỏ bộ nhớ đệm |
| Thẻ ứng viên đứng mãi ở "Đang chấm" hoặc "Không chấm được" | Xem `/health`: Gemini hết hạn mức hoặc Ollama chưa chạy. Đổi `AI_PROVIDER` trong `.env` rồi khởi động lại backend |
| Bị đưa về màn hình đăng nhập | Token hết hạn (7 ngày) hoặc không hợp lệ: đăng nhập lại |

### 5.5. Kiểm thử Backend
Khi server đang chạy, mở một terminal khác tại `backend/` và chạy toàn bộ kiểm thử. Lệnh này kiểm tra môi trường, chạy unit test, smoke test API và End-to-End luồng AI, rồi tự ghi báo cáo có mốc thời gian vào `docs/Test-Reports/`:
```powershell
.\venv\Scripts\python.exe scripts\run_backend_tests.py --cleanup-first --note "Lý do test"
```
- Hướng dẫn chi tiết và tiêu chí đạt: [docs/Huong dan kiem thu Backend.md](docs/Huong%20dan%20kiem%20thu%20Backend.md)
- Lịch sử các lần test: [docs/Test-Reports/README.md](docs/Test-Reports/README.md)
- Các vấn đề đã phát hiện: [docs/Issues/README.md](docs/Issues/README.md)

---

## 📡 6. Danh sách API Chính Hiện Có

| Phương thức | Đường dẫn API | Quyền hạn | Mô tả |
|---|---|---|---|
| `GET` | `/health` | Public | Kiểm tra tình trạng hoạt động server |
| `POST` | `/api/auth/login` | Public | Đăng nhập tài khoản HR lấy JWT Token |
| `GET` | `/api/jobs/open` | Public | Lấy danh sách việc làm đang mở cho ứng viên |
| `GET` | `/api/jobs` | Public | Lấy toàn bộ danh sách việc làm (có lọc theo trạng thái) |
| `POST` | `/api/jobs` | HR / Admin | Đăng tin tuyển dụng mới |
| `GET` | `/api/jobs/{id}` | Public | Xem chi tiết 1 tin tuyển dụng |
| `PUT` | `/api/jobs/{id}` | HR / Admin | Cập nhật thông tin tin tuyển dụng |
| `PATCH` | `/api/jobs/{id}/close` | HR / Admin | Đóng tin tuyển dụng không nhận thêm hồ sơ |
| `POST` | `/api/applications/apply` | Public | Ứng viên nộp hồ sơ đính kèm file CV (backend nhận .pdf/.docx; giao diện hiện chỉ cho chọn .pdf) |
| `GET` | `/api/applications` | HR / Admin | Lấy danh sách hồ sơ ứng tuyển theo Job ID / Status |
| `GET` | `/api/applications/{id}` | HR / Admin | Chi tiết một hồ sơ kèm ứng viên và tin tuyển dụng |
| `PATCH` | `/api/applications/{id}/status` | HR / Admin | Cập nhật trạng thái ứng viên khi kéo thả Kanban |
| `GET` | `/api/applications/{id}/ai-analysis` | HR / Admin | Kết quả AI: điểm, kỹ năng khớp / thiếu, thông tin bóc tách, câu hỏi phỏng vấn |
| `GET` | `/api/applications/{id}/cv` | HR / Admin | Tệp CV gốc của ứng viên |

---

## 👥 7. Thành viên Thực hiện
- **Dự án:** SmartRecruit AI (Nhóm 02 thành viên)
- **Tiến độ chi tiết:** Xem tại file [`checklist.md`](./checklist.md)

