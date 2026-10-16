"""
Script tạo bộ 03 CV mẫu (PDF tiếng Việt) theo kịch bản kiểm thử Mục 8.1,
đối chiếu với tin tuyển dụng "Backend Developer (Python/FastAPI)" (Job seed số 1):

    CV 1: Rất phù hợp với JD              → kỳ vọng Matching Score > 85%
    CV 2: Trái ngành / không liên quan    → kỳ vọng Matching Score < 40%
    CV 3: Khác từ ngữ nhưng đồng nghĩa    → kiểm tra Semantic Matching

Chạy:  python scripts/generate_sample_cvs.py
Kết quả: backend/tests/fixtures/sample_cvs/*.pdf
Yêu cầu: pip install fpdf2 (chỉ dùng cho kiểm thử, không nằm trong requirements.txt)
"""
import sys
from pathlib import Path

try:
    from fpdf import FPDF
except ImportError:
    sys.exit("Chưa cài fpdf2. Chạy: pip install fpdf2")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "sample_cvs"

# Font Unicode hỗ trợ tiếng Việt (Windows: Arial; Linux: DejaVu Sans)
FONT_CANDIDATES = [
    (Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/arialbd.ttf")),
    (Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")),
]

SAMPLE_CVS = {
    "CV1_phu_hop_backend_python.pdf": {
        "name": "Nguyễn Minh Khoa",
        "title": "Backend Developer - Python",
        "contact": "Email: khoa.nguyen.dev@example.com | SĐT: 0912 345 678 | Hà Nội",
        "sections": [
            ("MỤC TIÊU NGHỀ NGHIỆP", [
                "Backend Developer với hơn 3 năm kinh nghiệm xây dựng RESTful API hiệu năng cao bằng Python và FastAPI. "
                "Mong muốn đóng góp vào các hệ thống quy mô lớn trong lĩnh vực tuyển dụng và nhân sự.",
            ]),
            ("KỸ NĂNG", [
                "- Ngôn ngữ: Python, SQL",
                "- Framework: FastAPI, Flask, Pydantic",
                "- Cơ sở dữ liệu & ORM: MySQL, SQLAlchemy, Alembic, Redis",
                "- DevOps: Docker, Docker Compose, Linux (Ubuntu), Git, GitHub Actions CI/CD",
                "- Kiến thức: RESTful API, JWT/OAuth2, kiến trúc microservices, unit test với pytest",
            ]),
            ("KINH NGHIỆM LÀM VIỆC", [
                "Công ty CP Công nghệ TopCV - Backend Developer (03/2023 - nay)",
                "- Phát triển các RESTful API bằng FastAPI và SQLAlchemy trên MySQL cho hệ thống ATS phục vụ 2.000 doanh nghiệp.",
                "- Tối ưu truy vấn MySQL và bổ sung cache Redis, giảm 40% thời gian phản hồi API.",
                "- Đóng gói dịch vụ bằng Docker, triển khai trên máy chủ Linux qua GitHub Actions.",
                "",
                "Công ty TNHH Phần mềm FPT - Python Developer (07/2021 - 02/2023)",
                "- Xây dựng API quản lý hồ sơ nhân sự bằng Flask và SQLAlchemy, viết unit test với pytest.",
                "- Tham gia chuyển đổi hệ thống từ Flask sang FastAPI xử lý bất đồng bộ.",
            ]),
            ("HỌC VẤN", [
                "Đại học Bách khoa Hà Nội - Kỹ sư Công nghệ Thông tin (2017 - 2021), GPA 3.4/4",
            ]),
            ("CHỨNG CHỈ", [
                "- TOEIC 820",
                "- AWS Certified Cloud Practitioner",
            ]),
        ],
    },
    "CV2_trai_nganh_ke_toan.pdf": {
        "name": "Trần Thị Hồng Nhung",
        "title": "Kế toán tổng hợp",
        "contact": "Email: nhung.tran.kt@example.com | SĐT: 0987 654 321 | TP. Hồ Chí Minh",
        "sections": [
            ("MỤC TIÊU NGHỀ NGHIỆP", [
                "Kế toán tổng hợp với 5 năm kinh nghiệm trong lĩnh vực thương mại và sản xuất. "
                "Mục tiêu trở thành Kế toán trưởng trong 3 năm tới.",
            ]),
            ("KỸ NĂNG", [
                "- Thành thạo phần mềm kế toán MISA, Fast Accounting",
                "- Sử dụng Excel nâng cao (VLOOKUP, Pivot Table), Word",
                "- Lập báo cáo tài chính, báo cáo thuế GTGT, TNDN, TNCN",
                "- Quản lý công nợ, kiểm kê kho, đối chiếu ngân hàng",
                "- Kỹ năng giao tiếp, cẩn thận, chịu được áp lực công việc",
            ]),
            ("KINH NGHIỆM LÀM VIỆC", [
                "Công ty TNHH Thương mại Phú Thành - Kế toán tổng hợp (01/2022 - nay)",
                "- Hạch toán chứng từ, lập báo cáo tài chính quý và năm.",
                "- Kê khai, quyết toán thuế GTGT, TNDN; làm việc với cơ quan thuế.",
                "",
                "Công ty CP Sản xuất Bao bì Việt - Kế toán viên (06/2020 - 12/2021)",
                "- Theo dõi công nợ phải thu, phải trả; lập phiếu thu chi, đối chiếu sổ phụ ngân hàng.",
            ]),
            ("HỌC VẤN", [
                "Đại học Kinh tế TP. Hồ Chí Minh - Cử nhân Kế toán (2016 - 2020)",
            ]),
            ("CHỨNG CHỈ", [
                "- Chứng chỉ Kế toán trưởng",
                "- Tin học văn phòng MOS Excel",
            ]),
        ],
    },
    "CV3_dong_nghia_server_side.pdf": {
        "name": "Lê Hoàng Phúc",
        "title": "Kỹ sư phần mềm phía máy chủ (Server-side Engineer)",
        "contact": "Email: phuc.le.engineer@example.com | SĐT: 0905 111 222 | Đà Nẵng",
        "sections": [
            ("GIỚI THIỆU", [
                "Kỹ sư phần mềm 3 năm kinh nghiệm thiết kế và phát triển dịch vụ web phía máy chủ bằng ngôn ngữ Python. "
                "Am hiểu xây dựng giao diện lập trình ứng dụng theo kiến trúc REST và thiết kế cơ sở dữ liệu quan hệ.",
            ]),
            ("CHUYÊN MÔN", [
                "- Lập trình hướng đối tượng và xử lý bất đồng bộ (async/await) với Python",
                "- Framework web hiệu năng cao dựa trên chuẩn ASGI và Starlette, kiểm tra dữ liệu với Pydantic",
                "- Ánh xạ đối tượng - quan hệ (ORM), viết migration cho cơ sở dữ liệu",
                "- Hệ quản trị cơ sở dữ liệu quan hệ mã nguồn mở của Oracle, tối ưu chỉ mục và truy vấn",
                "- Bộ nhớ đệm in-memory, đóng gói ứng dụng bằng container, vận hành máy chủ Ubuntu",
                "- Quản lý phiên bản mã nguồn, quy trình tích hợp và triển khai liên tục",
            ]),
            ("KINH NGHIỆM LÀM VIỆC", [
                "Công ty TNHH Giải pháp Số Miền Trung - Kỹ sư phần mềm (05/2022 - nay)",
                "- Xây dựng dịch vụ web phía máy chủ cho nền tảng thương mại điện tử, phục vụ 50.000 người dùng mỗi ngày.",
                "- Thiết kế lược đồ cơ sở dữ liệu quan hệ, tối ưu truy vấn giúp giảm 35% độ trễ.",
                "- Đóng gói các dịch vụ thành container và triển khai trên máy chủ Ubuntu.",
                "",
                "Trung tâm Công nghệ Thông tin Đà Nẵng - Lập trình viên (09/2021 - 04/2022)",
                "- Phát triển giao diện lập trình ứng dụng phục vụ ứng dụng di động của thành phố.",
            ]),
            ("HỌC VẤN", [
                "Đại học Bách khoa - Đại học Đà Nẵng - Kỹ sư Khoa học Máy tính (2017 - 2021)",
            ]),
        ],
    },
}


def _load_fonts(pdf: FPDF) -> None:
    for regular, bold in FONT_CANDIDATES:
        if regular.exists() and bold.exists():
            pdf.add_font("CVFont", "", str(regular))
            pdf.add_font("CVFont", "B", str(bold))
            return
    sys.exit("Không tìm thấy font Unicode hỗ trợ tiếng Việt (Arial hoặc DejaVu Sans).")


def build_cv_pdf(cv: dict, output_path: Path) -> None:
    pdf = FPDF(format="A4")
    pdf.set_margins(18, 16, 18)
    pdf.set_auto_page_break(auto=True, margin=16)
    _load_fonts(pdf)
    pdf.add_page()

    pdf.set_font("CVFont", "B", 20)
    pdf.cell(0, 10, cv["name"], new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("CVFont", "B", 12)
    pdf.set_text_color(40, 90, 160)
    pdf.cell(0, 7, cv["title"], new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("CVFont", "", 10)
    pdf.cell(0, 6, cv["contact"], new_x="LMARGIN", new_y="NEXT")

    for heading, lines in cv["sections"]:
        pdf.ln(4)
        pdf.set_font("CVFont", "B", 12)
        pdf.cell(0, 7, heading, new_x="LMARGIN", new_y="NEXT")
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
        pdf.ln(1.5)
        pdf.set_font("CVFont", "", 10.5)
        for line in lines:
            if line:
                pdf.multi_cell(0, 5.5, line, new_x="LMARGIN", new_y="NEXT")
            else:
                pdf.ln(2)

    pdf.output(str(output_path))


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for filename, cv in SAMPLE_CVS.items():
        path = OUTPUT_DIR / filename
        build_cv_pdf(cv, path)
        print(f"✅ Đã tạo {path}")


if __name__ == "__main__":
    main()
