# 6.3 – Bảng Kanban 5 cột (`admin.html`)

**Ngày:** 17/10/2026 · **Nhánh:** `feature/frontend-tan` · **Màn hình:** A5, A8 (tài liệu Hướng dẫn phát triển Frontend, Mục 4.2)

> Làm chung đợt và chung commit với [6.4](Phan%206.4.md), [6.5](Phan%206.5.md), [6.6](Phan%206.6.md) (bạn duyệt gộp ngày 17/10/2026), vì 4 mục cùng dựa trên một bảng và một luồng kiểm thử. Bảng kiểm thử chung của cả 4 mục nằm ở cuối file này.

## Mục tiêu
Hiện hồ sơ của tin đang chọn trên 5 cột theo trạng thái backend (đã chốt 5 cột): Mới nộp, Sàng lọc, Phỏng vấn, Đề nghị nhận việc, Từ chối.

## Đã làm
- **Tải hồ sơ:** khi chọn tin, gọi `ApplicationAPI.list({ job_id, sort_by: "score_desc", limit: 500 })` **một lần**, rồi chia thẻ vào cột theo `status`.
  - Trong mỗi cột, thẻ giữ thứ tự API trả về: điểm cao → thấp, hồ sơ chưa có điểm xếp cuối. Như vậy đã đáp ứng luôn yêu cầu xếp theo điểm của mục 7.5 (chưa đánh dấu 7.5).
  - Hồ sơ có `status` lạ thì đưa vào cột *Mới nộp*.
- **Đầu cột:** chấm màu và số thẻ; cột *Mới nộp* có ghi chú "Hồ sơ mới, AI đang xử lý". Cột rỗng hiện "Kéo thẻ vào đây".
- **Dòng thống kê** dưới ô chọn tin: tổng số hồ sơ, số hồ sơ AI đang chấm.
- **3 trạng thái:**
  - Đang tải: spinner.
  - Rỗng: vẫn hiện 5 cột, kèm dòng "Tin này chưa có hồ sơ nào…".
  - Lỗi: báo lỗi kèm nút Thử lại.
- **A8 – tự cập nhật:**
  - Khi còn thẻ `ai_status` là `pending` / `processing`, cứ 7 giây gọi lại API một lần (không hiện spinner). Hết thẻ đang chấm thì dừng.
  - Chỉ vẽ lại bảng khi dữ liệu thật sự đổi.
  - Bỏ qua lượt gọi lại khi đang kéo thẻ hoặc đang chờ API đổi trạng thái.
  - Lỗi khi gọi lại: giữ nguyên bảng, lượt sau thử lại.
  - Dừng gọi lại khi đổi tin, tải lại trang, đăng xuất hoặc hết phiên. Có cơ chế bỏ kết quả cũ, để kết quả của tin trước không ghi đè lên tin vừa chọn.
- **Bấm vào thẻ** (hoặc Enter / Space khi thẻ đang được chọn): tạm hiện toast "Chi tiết hồ sơ sẽ có ở mục 6.7".

## File thay đổi (chung 6.3–6.6)
- `frontend/js/admin.js`: các hàm `loadApplications`, `renderBoard`, `cardHtml`, `cardBadge`, `initSortable`, `moveApplication`, gọi lại định kỳ (`schedulePoll` / `stopPolling`). Bỏ khung cột rỗng của 6.1.
- `frontend/css/style.css`: thêm `.kanban-list`, `.candidate-card.is-saving`, `.card-spinner`, `.card-menu-btn`, `.card-name`, `.app-stats`, viền khi chọn thẻ bằng bàn phím.
- `checklist.md`, `docs/Phan 6/Phan 6.3.md` → `Phan 6.6.md`, `docs/Phan 6/readme.md`.

## Kiểm thử (chung 6.3–6.6)
Backend thật `127.0.0.1:8000`, trang `127.0.0.1:5598/admin.html`. **Chỉ gọi AI thật 1 lần** (một lần nộp hồ sơ); các trạng thái AI khác đều giả lập.

| Ca | Cách thử | Kết quả |
| --- | --- | --- |
| Tin #3 (2 hồ sơ cũ) | Thật | Cả 2 nằm ở cột *Mới nộp*: thẻ 86% trước, thẻ "Không chấm được" sau; thống kê "2 hồ sơ" |
| Kéo thẻ #1 sang *Sàng lọc* bằng chuột | Thật | Thẻ sang cột mới, số thẻ đổi, toast "Đã chuyển…"; backend lưu `screening` |
| Chuyển cột khi API lỗi mạng | Giả lập (`updateStatus` trễ 0,8 s rồi lỗi) | Khi đang lưu: thẻ đã ở cột mới, mờ đi, không kéo được, bấm chuyển lần nữa thì bỏ qua. Khi lỗi: **thẻ về cột cũ**, toast đỏ nêu lý do |
| Menu ⋮ → *Mới nộp* | Thật | Thẻ #1 về cột *Mới nộp*, xếp đúng theo điểm; backend lưu `applied` |
| 9 hồ sơ đủ kiểu `ai_status` | Giả lập | 92 → xanh, 79,6 → hiện 80% xanh, 61 → vàng, 20 → đỏ; `pending` "Chờ AI", `processing` "Đang chấm"; `partial` có ⚠️, chú thích là `ai_error`; `failed` "Không chấm được", chú thích là `ai_error`; trạng thái lạ vào *Mới nộp* |
| Tên chứa `<img onerror>`, chức danh chứa `<script>` | Giả lập | Hiện nguyên văn, không chạy, không sinh thẻ `<img>` / `<script>` |
| Tự cập nhật | Giả lập | Lượt gọi lại sau 7 s cập nhật đúng thẻ; hết thẻ đang chấm thì dừng (sau 7,5 s nữa không gọi thêm) |
| Tin #2 chưa có hồ sơ | Thật | 5 cột rỗng kèm dòng "Tin này chưa có hồ sơ nào…", thống kê "0 hồ sơ" |
| Đang tải / lỗi → Thử lại | Giả lập lỗi, sau đó bấm Thử lại với API thật | Spinner; báo lỗi kèm nút Thử lại; bấm thì tải lại đúng |
| Token hỏng khi chuyển cột | Thật | 401, về màn hình đăng nhập, ngừng gọi lại; không hiện toast lỗi thừa; backend không đổi |
| **Nộp 1 hồ sơ thật** (`test.tan.kanban@example.com`, CV1 mẫu) rồi bấm Tải lại | Thật (Gemini) | Thẻ #56 "Đang chấm" ở cột *Sàng lọc*, thống kê "1 đang chấm AI"; **sau khoảng 35 s thẻ tự đổi sang 61%** kèm chức danh "Backend Developer - Python"; trang tự dừng gọi lại |
| Khổ 375px | Thật | Trang không tràn ngang; bảng cuộn ngang trong khung; menu ⋮ hiện đủ, không bị cắt |

Console: chỉ có lỗi 401 do **cố ý** dùng token giả. `node --check` đạt.

## Lưu ý
- Trang chỉ tự gọi lại API khi **đang có** thẻ AI chấm dở. Hồ sơ mới nộp khi bảng đang mở không tự hiện; HR bấm *Tải lại*. Đây đúng là cách A8 trong tài liệu mô tả.
- **Dữ liệu thử còn sót:**
  - Hồ sơ #56 (`test.tan.kanban@example.com`) ở tin #3. Dọn bằng `python scripts/e2e_test_pipeline.py --cleanup` tại `backend/`.
  - Hồ sơ #1 (của backend, `test_candidate@gmail.com`) đã được chuyển qua lại khi thử và **đã trả về `applied`** như ban đầu.
