# SmartRecruit AI 🚀
> **Hệ thống Quản lý Tuyển dụng Thông minh Kết hợp Trí tuệ Nhân tạo**  
> *Đồ án Cơ sở — Khoa Công nghệ Thông tin*

---

## 📖 1. Giới thiệu Dự án

**SmartRecruit AI** là một hệ thống ATS (Applicant Tracking System) hiện đại được thiết kế để giải quyết bài toán sàng lọc hồ sơ ứng viên tự động. Hệ thống hỗ trợ:
- **Cổng thông tin Ứng viên (Candidate Portal):** Xem việc làm đang mở, nộp hồ sơ trực tuyến đính kèm file CV (.pdf, .docx).
- **Cổng quản trị Nhân sự (HR Dashboard):** Quản lý tin tuyển dụng, xem danh sách ứng viên, quản lý quy trình tuyển dụng qua bảng Kanban kéo thả (SortableJS).
- **Công cụ Đánh giá AI (AI Engine - Đang tích hợp):** Kết hợp trích xuất văn bản từ CV, phân tích kỹ năng và tính điểm tương đồng ngữ nghĩa (Cosine Similarity & Google Gemini) để đưa ra gợi ý phỏng vấn và xếp hạng ứng viên.

---

## 🛠️ 2. Ngăn xếp Công nghệ (Tech Stack)

| Thành phần | Công nghệ sử dụng |
|---|---|
| **Kiến trúc** | Client – Server Monolith (Decoupled) |
| **Backend** | Python 3.10+, FastAPI, Uvicorn, Pydantic |
| **Database & ORM** | MySQL 8.0 (Cloud Aiven), SQLAlchemy 2.0, PyMySQL (SSL) |
| **Authentication** | JWT (JSON Web Token), SHA-256 Hashing |
| **Frontend** | HTML5, CSS3, JavaScript (ES6+), Bootstrap 5 (CDN), SortableJS |
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
│   ├── css/style.css       # File định dạng tùy chỉnh
│   ├── js/
│   │   ├── api.js          # API Client dùng chung
│   │   ├── index.js        # Script cho Cổng Ứng viên
│   │   └── admin.js        # Script cho Bảng Kanban của HR
│   ├── index.html          # Giao diện Cổng Ứng viên
│   └── admin.html          # Giao diện Bảng điều khiển Tuyển dụng (HR)
├── docs/                   # Tài liệu đề xuất, biên bản họp nhóm
├── .env                    # Biến môi trường bí mật (chứa connection string, API key)
├── .env.example            # Bản mẫu cấu hình môi trường
├── checklist.md            # Bảng theo dõi tiến độ chi tiết của dự án
└── README.md               # Tài liệu hướng dẫn dự án
```

---

## ⚙️ 4. Hướng dẫn Cài đặt & Thiết lập Môi trường

### 4.1. Chuẩn bị Môi trường
- Đã cài đặt **Python 3.10+** (khuyến nghị Python 3.12).
- Trình duyệt hiện đại (Chrome, Edge, Firefox).

### 4.2. Thiết lập Biến Môi trường (.env)
Tạo file `.env` tại thư mục gốc dự án dựa trên file `.env.example`:
```ini
# Database (Aiven MySQL Cloud)
DATABASE_URL=mysql+pymysql://avnadmin:<password>@<host>:<port>/defaultdb?ssl_disabled=false

# Google Gemini AI Key
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash
AI_PROVIDER=cloud

# Bảo mật & Tệp
SECRET_KEY=your_random_secret_key_here
UPLOAD_DIR=uploads/cv
MAX_UPLOAD_SIZE_MB=5
```

### 4.3. Cài đặt Thư viện Python
Mở Terminal tại thư mục `backend/` và kích hoạt venv:
```powershell
cd D:\3\DoAnCoSo\backend
.\venv\bin\python.exe -m pip install -r requirements.txt
```

### 4.4. Khởi tạo Cơ sở Dữ liệu & Nạp Dữ liệu Mẫu
Chạy 2 script sau để đồng bộ bảng lên Cloud Aiven MySQL và tạo dữ liệu ban đầu:

```powershell
# 1. Tạo cấu trúc các bảng CSDL
.\venv\bin\python.exe init_db.py

# 2. Seed dữ liệu mẫu (1 HR, 2 tin tuyển dụng lập trình viên)
.\venv\bin\python.exe seed_db.py
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
.\venv\bin\python.exe -m uvicorn app.main:app --reload
```

- **Swagger UI (Tài liệu API tương tác):** 👉 [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Kiểm tra trạng thái (Health Check):** 👉 [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### 5.2. Chạy Frontend
- Mở trực tiếp các file HTML trong trình duyệt hoặc sử dụng extension **Live Server** trong VS Code:
  - **Cổng Ứng viên:** Mở file `frontend/index.html`
  - **Bảng Quản trị HR:** Mở file `frontend/admin.html`

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
| `POST` | `/api/applications/apply` | Public | Ứng viên nộp hồ sơ đính kèm file CV (.pdf/.docx) |
| `GET` | `/api/applications` | HR / Admin | Lấy danh sách hồ sơ ứng tuyển theo Job ID / Status |
| `PATCH` | `/api/applications/{id}/status` | HR / Admin | Cập nhật trạng thái ứng viên khi kéo thả Kanban |

---

## 👥 7. Thành viên Thực hiện
- **Dự án:** SmartRecruit AI (Nhóm 02 thành viên)
- **Tiến độ chi tiết:** Xem tại file [`checklist.md`](./checklist.md)

