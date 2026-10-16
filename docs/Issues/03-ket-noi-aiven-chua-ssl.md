# 03 – Kết nối Aiven MySQL chưa mã hóa SSL

**Mức độ:** 🟠 Trung bình (bảo mật)
**Thành phần:** `backend/app/core/database.py`
**Checklist:** Mục 2.1 – "Cấu hình kết nối SQLAlchemy và PyMySQL với Aiven Cloud (hỗ trợ SSL)" (chưa hoàn thành)

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
