# 03 – Kết nối Aiven MySQL chưa mã hóa SSL

**Mức độ:** 🟠 Trung bình (bảo mật)
**Trạng thái:** ✅ Đã xử lý (16/10/2026) — mã hóa TLS 1.3; chế độ xác minh CA chờ tải chứng chỉ
**Thành phần:** `backend/app/core/database.py`
**Checklist:** Mục 2.1 – "Cấu hình kết nối SQLAlchemy và PyMySQL với Aiven Cloud (hỗ trợ SSL)" (đã đánh dấu hoàn thành)

## Hiện tượng

Kiểm tra trạng thái phiên kết nối tới Aiven MySQL 8.4.8:

```sql
SHOW SESSION STATUS LIKE 'Ssl_cipher';
-- Kết quả: ('Ssl_cipher', '')   ← rỗng nghĩa là không mã hóa
```

## Nguyên nhân

Trong `database.py`, cấu hình SSL vẫn đang bị comment:

```python
engine = create_engine(
    DATABASE_URL,
    # Aiven MySQL requires SSL; add connect_args here when using real cloud URL
    # connect_args={"ssl": {"ca": "/path/to/ca.pem"}},
    ...
)
```

`DATABASE_URL` dạng `mysql+pymysql://` không truyền `ssl-mode` cho PyMySQL, nên kết nối đi qua Internet dưới dạng văn bản thường.

## Ảnh hưởng

Các dữ liệu sau truyền qua mạng không được mã hóa:
- Mật khẩu CSDL (`avnadmin`).
- Thông tin cá nhân của ứng viên: họ tên, email, số điện thoại, toàn văn CV.

Khi dùng mạng công cộng (Wi-Fi trường, quán cà phê), dữ liệu có thể bị nghe lén. Đây cũng là điểm dễ bị hỏi khi bảo vệ đồ án, vì hệ thống lưu dữ liệu cá nhân.

## Hướng xử lý

1. Tải chứng chỉ CA của dịch vụ (Aiven Console → Overview → CA certificate) và lưu tại `backend/certs/aiven-ca.pem`. Thêm thư mục `backend/certs/` vào `.gitignore` nếu cần.
2. Thêm biến `DB_SSL_CA` vào `config.py` và `.env.example`.
3. Truyền `connect_args={"ssl": {"ca": DB_SSL_CA}}` khi có CA. Nếu chưa có CA, vẫn bật SSL nhưng không xác minh chứng chỉ, kèm cảnh báo trong log.
4. Kiểm tra lại: `Ssl_cipher` phải trả về một bộ mã hóa, ví dụ `TLS_AES_256_GCM_SHA384`.

Ước tính: khoảng 10 phút. Có thể làm độc lập với kế hoạch 4.9.

## Kết quả xử lý (16/10/2026) — ✅ Đã xử lý

**Nguyên nhân gốc (phát hiện khi sửa):** `DATABASE_URL` có tham số `?ssl_disabled=false`. SQLAlchemy truyền giá trị này cho PyMySQL dưới dạng **chuỗi** `"false"`. Chuỗi khác rỗng là truthy trong Python, nên PyMySQL hiểu thành `ssl_disabled=True` và **tắt SSL**. Chỉ bật `connect_args` thì chưa đủ.

**Đã sửa trong `backend/app/core/database.py`:**
- Tự loại bỏ các tham số SSL (`ssl_disabled`, `ssl-mode`, `sslmode`...) khỏi query string của `DATABASE_URL`. SSL chỉ cấu hình qua biến `DB_SSL_MODE`.
- `DB_SSL_MODE` có 4 chế độ:
  - `auto` (mặc định): có `DB_SSL_CA` thì dùng `verify`; máy chủ cloud thì dùng `required`; localhost thì dùng `disabled`.
  - `verify`: TLS + xác minh chứng chỉ bằng CA của Aiven + kiểm tra hostname.
  - `required`: mã hóa TLS nhưng không xác minh chứng chỉ.
  - `disabled`: không mã hóa.
- `get_connection_security()` đọc `Ssl_version` / `Ssl_cipher` của phiên kết nối. Kết quả hiển thị ở `/health` → `database`.
- Unit test: `backend/tests/test_database_ssl.py` (10 bài).

**Kiểm thử thật:**

```json
"database": {"encrypted": true, "tls_version": "TLSv1.3", "cipher": "TLS_AES_256_GCM_SHA384"}
```

**Còn lại (tùy chọn, khuyến nghị trước khi demo):** hiện đang ở chế độ `required`, đã mã hóa nhưng chưa xác minh máy chủ. Để bật `verify`:
1. Tải CA certificate tại Aiven Console → dịch vụ MySQL → Overview → **CA certificate**.
2. Lưu thành `backend/certs/aiven-ca.pem` (thư mục `backend/certs/` đã có trong `.gitignore`).
3. Thêm vào `.env`: `DB_SSL_CA=certs/aiven-ca.pem`.
