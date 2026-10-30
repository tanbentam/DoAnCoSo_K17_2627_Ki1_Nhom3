"""
services/email_templates.py — Nội dung 4 mẫu email gửi ứng viên (Mục 7.2 – 7.4)

Mỗi hàm trả về EmailContent(subject, text, html). Mọi dữ liệu do người dùng nhập
(họ tên, tên vị trí, địa điểm) đều được escape trước khi chèn vào HTML.
"""
import html
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Sequence, Tuple

from app.core import config

# Giờ Việt Nam (UTC+7, không có giờ mùa hè) — CSDL lưu giờ UTC
VN_TZ = timezone(timedelta(hours=7), "ICT")

_WEEKDAYS = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]

Paragraph = str                       # chuỗi thường, chưa escape
Details = Sequence[Tuple[str, str]]   # [(nhãn, giá trị)] hiện thành bảng


@dataclass
class EmailContent:
    subject: str
    text: str
    html: str


def format_vn_datetime(value: datetime) -> str:
    """VD: '09:30, Thứ Hai 26/10/2026'. Giờ không kèm múi giờ được hiểu là UTC."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    local = value.astimezone(VN_TZ)
    return f"{local:%H:%M}, {_WEEKDAYS[local.weekday()]} {local:%d/%m/%Y}"


def _bold(paragraph: str, highlights: Sequence[str]) -> str:
    """Escape đoạn văn rồi in đậm các cụm trong highlights (đã escape cùng cách)."""
    out = html.escape(paragraph)
    for h in highlights:
        if h:
            esc = html.escape(h)
            out = out.replace(esc, f"<b>{esc}</b>", 1)
    return out


def _render(
    title: str,
    candidate_name: str,
    before: List[Paragraph],
    details: Optional[Details] = None,
    after: Optional[List[Paragraph]] = None,
    highlights: Sequence[str] = (),
) -> Tuple[str, str]:
    """Dựng bản chữ thường và bản HTML từ cùng một nội dung."""
    company = config.COMPANY_NAME
    after = after or []

    # Bản chữ thường
    lines = [f"Chào {candidate_name},", ""]
    for p in before:
        lines += [p, ""]
    if details:
        lines += [f"- {k}: {v}" for k, v in details] + [""]
    for p in after:
        lines += [p, ""]
    lines += ["Trân trọng,", f"Phòng Nhân sự {company}"]
    text = "\n".join(lines)

    # Bản HTML
    def para(p: str) -> str:
        return f'<p style="margin:0 0 14px">{_bold(p, highlights)}</p>'

    table = ""
    if details:
        rows = "".join(
            f'<tr><td style="padding:6px 16px 6px 0;color:#667085;white-space:nowrap;vertical-align:top">{html.escape(k)}</td>'
            f'<td style="padding:6px 0;font-weight:600">{html.escape(v)}</td></tr>'
            for k, v in details
        )
        table = (
            '<table role="presentation" cellpadding="0" cellspacing="0" '
            f'style="border-collapse:collapse;margin:0 0 16px;width:100%;background:#f5f7fb;border-radius:8px">'
            f'<tr><td style="padding:10px 16px"><table role="presentation" style="border-collapse:collapse">{rows}</table></td></tr></table>'
        )
    company_html = html.escape(company)
    body = (
        f'<p style="margin:0 0 14px">Chào <b>{html.escape(candidate_name)}</b>,</p>'
        + "".join(para(p) for p in before)
        + table
        + "".join(para(p) for p in after)
    )
    page = f"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title></head>
<body style="margin:0;padding:24px 12px;background:#eef1f6;font-family:Arial,Helvetica,sans-serif;color:#1d2939;font-size:15px;line-height:1.6">
  <div style="max-width:600px;margin:0 auto;background:#ffffff;border-radius:12px;overflow:hidden">
    <div style="background:#206bc4;color:#ffffff;padding:18px 24px;font-size:18px;font-weight:700">{company_html}</div>
    <div style="padding:24px">
      <h1 style="font-size:20px;line-height:1.3;margin:0 0 16px">{html.escape(title)}</h1>
      {body}
      <p style="margin:24px 0 0">Trân trọng,<br><b>Phòng Nhân sự {company_html}</b></p>
    </div>
    <div style="padding:12px 24px;background:#f9fafb;color:#98a2b3;font-size:12px">
      Thư được gửi tự động từ hệ thống tuyển dụng {company_html}.
    </div>
  </div>
</body></html>"""
    return text, page


def _subject(kind: str, job_title: str) -> str:
    return f"[{config.COMPANY_NAME}] {kind} - {job_title}"


def application_received(candidate_name: str, job_title: str) -> EmailContent:
    """Mẫu 1 (7.2): xác nhận đã nhận hồ sơ, gửi ngay sau khi ứng viên nộp."""
    company = config.COMPANY_NAME
    title = "Đã nhận hồ sơ ứng tuyển"
    text, page = _render(
        title,
        candidate_name,
        before=[
            f"Cảm ơn bạn đã quan tâm và ứng tuyển vị trí {job_title} tại {company}. "
            "Chúng tôi đã nhận được hồ sơ của bạn.",
            "Bộ phận tuyển dụng sẽ xem xét hồ sơ và liên hệ với bạn qua email này nếu hồ sơ phù hợp "
            "với các bước tiếp theo. Bạn không cần nộp lại hồ sơ cho vị trí này.",
        ],
        highlights=[job_title],
    )
    return EmailContent(_subject("Xác nhận đã nhận hồ sơ", job_title), text, page)


def interview_invitation(
    candidate_name: str,
    job_title: str,
    interview_at: Optional[datetime] = None,
    location: Optional[str] = None,
) -> EmailContent:
    """Mẫu 2 (7.3): thư mời phỏng vấn. Chưa có giờ / địa điểm thì báo HR sẽ liên hệ để thống nhất."""
    company = config.COMPANY_NAME
    pending = "Bộ phận tuyển dụng sẽ liên hệ để thống nhất"
    location = (location or "").strip()
    details = [
        ("Vị trí", job_title),
        ("Thời gian", f"{format_vn_datetime(interview_at)} (giờ Việt Nam)" if interview_at else pending),
        ("Địa điểm", location or pending),
    ]
    if interview_at:
        after = [
            "Vui lòng trả lời email này để xác nhận tham dự. Nếu thời gian chưa phù hợp, "
            "bạn hãy báo lại sớm để chúng tôi sắp xếp lịch khác.",
        ]
    else:
        after = ["Chúng tôi sẽ liên hệ với bạn trong thời gian sớm nhất để thống nhất lịch phỏng vấn phù hợp."]
    text, page = _render(
        "Thư mời phỏng vấn",
        candidate_name,
        before=[
            f"Cảm ơn bạn đã ứng tuyển vị trí {job_title}. Sau khi xem xét hồ sơ, {company} "
            "trân trọng mời bạn tham gia buổi phỏng vấn với thông tin như sau:",
        ],
        details=details,
        after=after,
        highlights=[job_title],
    )
    return EmailContent(_subject("Thư mời phỏng vấn", job_title), text, page)


def offer_letter(candidate_name: str, job_title: str) -> EmailContent:
    """Mẫu 3a (7.4): thông báo trúng tuyển (Offer Letter)."""
    company = config.COMPANY_NAME
    text, page = _render(
        "Chúc mừng bạn đã trúng tuyển",
        candidate_name,
        before=[
            f"{company} trân trọng thông báo bạn đã vượt qua vòng tuyển chọn cho vị trí {job_title}. "
            "Chúc mừng bạn!",
            "Bộ phận Nhân sự sẽ liên hệ với bạn trong vài ngày tới để trao đổi chi tiết về mức đãi ngộ, "
            "ngày bắt đầu làm việc và các giấy tờ cần chuẩn bị.",
            "Rất mong được chào đón bạn gia nhập đội ngũ của chúng tôi.",
        ],
        highlights=[job_title],
    )
    return EmailContent(_subject("Thông báo trúng tuyển", job_title), text, page)


def rejection_letter(candidate_name: str, job_title: str) -> EmailContent:
    """Mẫu 3b (7.4): thư cảm ơn và thông báo chưa phù hợp."""
    company = config.COMPANY_NAME
    text, page = _render(
        "Kết quả ứng tuyển",
        candidate_name,
        before=[
            f"Cảm ơn bạn đã dành thời gian quan tâm và ứng tuyển vị trí {job_title} tại {company}.",
            "Sau khi cân nhắc kỹ, chúng tôi rất tiếc phải thông báo hồ sơ của bạn chưa phù hợp với "
            "yêu cầu của vị trí ở thời điểm hiện tại.",
            "Chúng tôi sẽ lưu lại hồ sơ của bạn và liên hệ khi có cơ hội phù hợp hơn. "
            "Chúc bạn nhiều thành công trên con đường sự nghiệp.",
        ],
        highlights=[job_title],
    )
    return EmailContent(_subject("Kết quả ứng tuyển", job_title), text, page)
