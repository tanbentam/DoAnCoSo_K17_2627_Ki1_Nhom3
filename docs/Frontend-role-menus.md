# Menu dùng chung theo vai trò

- Menu ứng viên: `frontend/components/user-menu.html`.
- Menu HR: `frontend/components/hr-menu.html`.
- Bộ nạp: `frontend/js/shared/role-menu.js`.
- Kiểu hiển thị: `frontend/css/role-menu.css`.

Chạy frontend qua HTTP server hoặc Live Server. Không mở bằng `file://`, vì menu được tải bằng `fetch`.

## Tái sử dụng trên trang mới

Với trang nằm trực tiếp trong `frontend/user/` hoặc `frontend/admin/`, thêm vào head:

```html
<link rel="stylesheet" href="../css/style.css?v=3" />
<link rel="stylesheet" href="../css/role-menu.css?v=1" />
```

Chọn **một** vị trí menu phù hợp vai trò:

```html
<div data-role-menu="user"></div>
```

hoặc:

```html
<div data-role-menu="hr"></div>
```

Thêm trước thẻ đóng body:

```html
<script src="../js/shared/role-menu.js"></script>
```

Nếu trang nằm sâu hơn, điều chỉnh đường dẫn CSS/script theo vị trí HTML. Các URL trong menu tự được giải quyết theo vị trí `role-menu.js`, không theo độ sâu trang.

Menu HR phải nằm trong phần nội dung được app ẩn khi chưa đăng nhập. Menu không xác thực tài khoản: backend vẫn phải kiểm tra token và quyền trên mọi API HR.

## Thêm liên kết chức năng

Chỉ sửa file menu của vai trò tương ứng; mọi trang dùng menu đó sẽ nhận thay đổi sau khi tải lại:

```html
<a class="role-menu-link"
   data-menu-page="admin/ten-trang-da-tao.html"
   data-menu-target="id-khu-vuc">
  <span class="role-menu-icon" aria-hidden="true">03</span>
  <span><strong>Tên chức năng</strong><small>Mô tả ngắn</small></span>
</a>
```

Đây là mẫu; chỉ thêm khi file đích thực sự tồn tại. `data-menu-page` tính từ thư mục `frontend/`; `data-menu-target` không bắt buộc trên trang riêng. Bộ nạp chỉ chấp nhận URL cùng origin và cùng thư mục vai trò (`user/` hoặc `admin/`).

Hiện menu liên kết tới các khu vực trong hai trang hiện có. Khu vực Kanban vẫn là phần chờ A5; menu không tự tạo chức năng Kanban, chi tiết AI hoặc xem CV.
