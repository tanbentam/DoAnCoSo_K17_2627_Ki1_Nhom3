# Phần 5 – Cổng ứng viên (Frontend): nhật ký thực hiện

Mỗi mục trong `checklist.md` Mục 5 có một file log riêng: làm gì, file nào, kiểm thử ra sao, còn gì để ý.

- **Nhánh:** `feature/frontend-tan` (làm song song với nhánh frontend của thành viên khác, nhóm duyệt khi gộp).
- **Tài liệu liên quan:** [Huong dan phat trien Frontend.md](../Huong%20dan%20phat%20trien%20Frontend.md), [API cho Frontend.md](../API%20cho%20Frontend.md).

| File | Mục checklist | Trạng thái | Commit |
| --- | --- | --- | --- |
| [Phan 5.0.md](Phan%205.0.md) | Chuẩn bị: giao diện, `api.js`, `utils.js` | Xong | `419c45f`, `949c76e` (log: `6f8c9f1`) |
| [Phan 5.1.md](Phan%205.1.md) | 5.1 Danh sách tin tuyển dụng | Xong | `6f8c9f1` |
| [Phan 5.2.md](Phan%205.2.md) | 5.2 Modal chi tiết JD | Xong | `746392a` |
| [Phan 5.3.md](Phan%205.3.md) | 5.3 Form nộp CV | Xong | `c47275a` |
| [Phan 5.4.md](Phan%205.4.md) | 5.4 Kiểm tra tệp | Xong | `a415ff9` |
| [Phan 5.5.md](Phan%205.5.md) | 5.5 Gửi `FormData` | Xong | `cb5641f` |
| [Phan 5.6.md](Phan%205.6.md) | 5.6 Trạng thái nộp hồ sơ | Xong | |

**Mẫu một file log:** Mục tiêu → Đã làm → File thay đổi → Kiểm thử → Lưu ý / việc còn lại.

## Tổng kết Phần 5 (17/10/2026)
Cổng ứng viên chạy trọn luồng với backend thật: xem danh sách việc → mở JD → điền form → kiểm tra dữ liệu và tệp → gửi → báo thành công hoặc lỗi. Code nằm ở `frontend/index.html` và `frontend/js/index.js`; phần dùng chung ở `api.js`, `utils.js`, `css/style.css`.

**Việc còn mở:**
- Nhóm chốt có nhận CV `.docx` hay không (hiện chỉ nhận PDF, xem [Phan 5.4.md](Phan%205.4.md)).
- Dọn dữ liệu thử: hồ sơ #55 (`test.tan@example.com`) bằng `python scripts/e2e_test_pipeline.py --cleanup` tại `backend/`.
- Tin #3 có `preferred_skills = ["string"]` (dữ liệu tạo từ Swagger): báo backend sửa hoặc đóng tin trước khi demo.
