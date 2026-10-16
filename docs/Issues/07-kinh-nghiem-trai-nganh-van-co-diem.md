# 07 – Kinh nghiệm trái ngành vẫn được tính đủ điểm

**Mức độ:** 🟡 Thấp (cần thảo luận, không hẳn là lỗi)
**Thành phần:** `backend/app/services/hybrid_scoring.py`
**Hồ sơ minh họa:** Application #5 (CV2 – Kế toán)

## Hiện tượng

CV2 (kế toán, 6.4 năm kinh nghiệm) nộp vào vị trí Backend Developer:

| Tiêu chí Hard Filter | Trọng số | Điểm |
| --- | --- | --- |
| Kỹ năng bắt buộc | 60% | 0 |
| Kinh nghiệm (yêu cầu 2 năm) | 25% | **100** |
| Kỹ năng ưu tiên | 15% | 0 |
| **Hard Filter** | | **25** |

6.4 năm làm kế toán được tính như 6.4 năm kinh nghiệm lập trình backend.

## Nguyên nhân

`experience_score()` chỉ so sánh tổng số năm kinh nghiệm với `experience_years_min`. Hàm không xét kinh nghiệm đó có liên quan tới vị trí ứng tuyển hay không.

## Ảnh hưởng

- Điểm cuối vẫn đúng kỳ vọng: CV2 được 10 điểm (dưới 40), vì Semantic Score bằng 0 và không khớp kỹ năng nào.
- Nhưng ứng viên trái ngành luôn nhận sẵn tới 10 điểm Matching (25 × 40%) chỉ nhờ số năm đi làm.
- Hội đồng có thể hỏi điểm này khi xem phần giải thích điểm trên giao diện HR.

## Hướng xử lý (cần thống nhất trong nhóm)

- **Phương án 1 – Nhân theo độ phù hợp kỹ năng:** điểm kinh nghiệm × tỷ lệ kỹ năng bắt buộc khớp. Ứng viên không khớp kỹ năng nào thì điểm kinh nghiệm bằng 0. Đơn giản, dễ giải thích.
- **Phương án 2 – Chỉ tính kinh nghiệm liên quan:** dùng embedding so `position` / `description` của từng mục `work_experience` với JD, chỉ cộng các mục đủ giống. Chính xác hơn, nhưng phức tạp và chạy chậm hơn.
- **Phương án 3 – Giữ nguyên:** vì Semantic Score đã kéo điểm CV trái ngành xuống đủ thấp. Ghi rõ giới hạn này trong báo cáo đồ án.
