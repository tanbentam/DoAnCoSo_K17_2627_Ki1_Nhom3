"""
services/text_cleaner.py — Module xử lý làm sạch và chuẩn hóa chuỗi văn bản (CV, JD, hồ sơ ứng viên)

Các tác vụ chính:
1. Chuẩn hóa mã hóa ký tự Unicode (NFKC) hỗ trợ tiếng Việt có dấu.
2. Loại bỏ các ký tự điều khiển (control characters), null bytes, form feeds và ký tự ẩn.
3. Chuẩn hóa ký tự danh sách (bullet points) thành định dạng markdown '- '.
4. Nối lại các từ bị ngắt dòng do dấu gạch nối (hyphenation at line breaks).
5. Xóa bỏ khoảng trắng thừa, tab thừa và ngắt dòng dư thừa liên tiếp.
6. Bảo toàn nguyên vẹn các thuật ngữ kỹ thuật, kỹ năng lập trình (C++, C#, .NET, CI/CD, v.v.).
"""

import logging
import re
import unicodedata
from typing import Optional

logger = logging.getLogger(__name__)

# Ký tự điều khiển ASCII và Unicode không in được cần loại bỏ
# (Giữ lại \t, \n, \r trong bước đầu, sau đó chuẩn hóa)
CONTROL_CHAR_REGEX = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\ufeff\ufffd\u200b-\u200d\u2060]"
)

# Ký tự bullet đa dạng thường gặp trong file PDF của CV
BULLET_REGEX = re.compile(
    r"(?m)^([ \t]*)[•●○■▪▫◆◇►▸✓✔★☆➢➤*][ \t]*"
)

# Dòng phân cách trang trí lặp lại (---, ===, ___, ~~~ từ 3 ký tự trở lên)
DECORATIVE_SEPARATOR_REGEX = re.compile(
    r"(?m)^[ \t]*[-=_~*]{3,}[ \t]*$"
)

# Từ bị ngắt dòng do dấu gạch nối cuối dòng trong PDF (ví dụ: "implemen-\n tation" -> "implementation")
HYPHENATED_LINEBREAK_REGEX = re.compile(
    r"(\b[A-Za-z0-9]+)-\s*\n\s*([A-Za-z0-9]+\b)"
)

# Nhiều khoảng trắng và tab liên tiếp trên cùng một dòng
HORIZONTAL_WHITESPACE_REGEX = re.compile(r"[ \t]+")

# 3 hoặc nhiều dòng trống liên tiếp
EXCESSIVE_NEWLINES_REGEX = re.compile(r"\n{3,}")


def remove_control_characters(text: str) -> str:
    """
    Loại bỏ các ký tự điều khiển (ASCII control chars), form feed (\x0c),
    null byte (\x00), BOM (\ufeff), zero-width spaces (\u200b-\u200d).
    """
    if not text:
        return ""
    return CONTROL_CHAR_REGEX.sub("", text)


def normalize_unicode(text: str) -> str:
    """
    Chuẩn hóa chuỗi theo chuẩn Unicode NFKC:
    - Đồng bộ hóa các ký tự tiếng Việt dựng sẵn và tổ hợp.
    - Chuyển non-breaking space (\\u00a0), em-space thành khoảng trắng tiêu chuẩn.
    - Chuẩn hóa dấu nháy đơn, nháy kép cong thành dấu nháy chuẩn ASCII.
    """
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", text)
    # Thay thế các dạng khoảng trắng đặc biệt
    normalized = normalized.replace("\u00a0", " ")
    normalized = normalized.replace("\u2009", " ")
    normalized = normalized.replace("\u3000", " ")
    # Chuẩn hóa dấu nháy
    normalized = normalized.replace("“", '"').replace("”", '"')
    normalized = normalized.replace("‘", "'").replace("’", "'")
    return normalized


def normalize_bullet_points(text: str) -> str:
    """
    Chuyển đổi các ký tự bullet điểm đầu dòng thành dấu gạch ngang chuẩn markdown '- '.
    Ví dụ: '• Python, FastAPI' -> '- Python, FastAPI'
    """
    if not text:
        return ""
    return BULLET_REGEX.sub(r"\1- ", text)


def fix_hyphenated_linebreaks(text: str) -> str:
    """
    Khắc phục tình trạng từ bị ngắt đôi xuống dòng do dấu gạch nối cuối dòng từ layout PDF.
    Ví dụ: 'implemen-\\n tation' -> 'implementation'
    """
    if not text:
        return ""
    return HYPHENATED_LINEBREAK_REGEX.sub(r"\1\2", text)


def normalize_separators(text: str) -> str:
    """
    Chuẩn hóa các đường kẻ phân cách trang trí trong CV (như '-------------------')
    thành dấu ngắt phần '---' gọn gàng.
    """
    if not text:
        return ""
    return DECORATIVE_SEPARATOR_REGEX.sub("---", text)


def clean_whitespace_and_newlines(text: str, max_consecutive_newlines: int = 2) -> str:
    """
    Làm sạch các khoảng trắng và dòng ngắt dư thừa:
    - Chuẩn hóa ngắt dòng Windows (\\r\\n) và Mac (\\r) về chuẩn Unix (\\n).
    - Gom nhiều dấu cách hoặc tab liên tiếp thành một dấu cách duy nhất.
    - Cắt bỏ khoảng trắng ở đầu và cuối mỗi dòng.
    - Giới hạn tối đa số dòng trống liên tiếp (mặc định 2: tương đương 1 dòng trống giữa 2 đoạn văn).
    - Xóa khoảng trắng và dòng trống ở đầu và cuối toàn bộ văn bản.
    """
    if not text:
        return ""

    # 1. Chuẩn hóa ngắt dòng
    unified = text.replace("\r\n", "\n").replace("\r", "\n")

    # 2. Gom khoảng trắng ngang trong từng dòng
    unified = HORIZONTAL_WHITESPACE_REGEX.sub(" ", unified)

    # 3. Cắt khoảng trắng đầu và cuối từng dòng
    lines = [line.strip() for line in unified.split("\n")]
    unified = "\n".join(lines)

    # 4. Thu gọn dòng trống liên tiếp
    replacement = "\n" * max_consecutive_newlines
    unified = EXCESSIVE_NEWLINES_REGEX.sub(replacement, unified)

    return unified.strip()


def clean_text(text: Optional[str]) -> str:
    """
    Hàm làm sạch chuỗi văn bản tổng quát:
    Thực hiện tuần tự tất cả các bước chuẩn hóa cơ bản.

    Tham số:
        text: Chuỗi văn bản thô đầu vào.

    Trả về:
        str: Chuỗi văn bản sạch, chuẩn hóa, sẵn sàng cho xử lý NLP / AI.
    """
    if not text or not isinstance(text, str):
        return ""

    # Bước 1: Xóa ký tự điều khiển & ký tự rác
    result = remove_control_characters(text)

    # Bước 2: Chuẩn hóa Unicode & dấu tiếng Việt
    result = normalize_unicode(result)

    # Bước 3: Sửa lỗi ngắt từ cuối dòng
    result = fix_hyphenated_linebreaks(result)

    # Bước 4: Làm sạch khoảng trắng & ngắt dòng thừa
    result = clean_whitespace_and_newlines(result)

    return result


def clean_cv_text(text: Optional[str]) -> str:
    """
    Hàm làm sạch chuyên biệt dành cho văn bản CV và JD tuyển dụng:
    Ngoài các bước cơ bản, hàm chuẩn hóa thêm bullet points và đường phân cách trang trí.

    Đặc điểm:
    - Bảo toàn an toàn các kỹ năng công nghệ: C++, C#, .NET, CI/CD, React.js, Python 3.10+, v.v.
    - Chuẩn hóa danh sách đầu dòng (bullet points) về '- ' giúp LLM và Vector Embeddings dễ đọc hiểu.
    - Chuẩn hóa các đường viền trang trí.
    - Giảm số lượng token dư thừa không cần thiết khi gửi lên Gemini API.

    Tham số:
        text: Văn bản thô trích xuất từ file PDF / DOCX của CV.

    Trả về:
        str: Văn bản CV sạch sẽ, có cấu trúc rõ ràng.
    """
    if not text or not isinstance(text, str):
        return ""

    # Bước 1: Loại bỏ ký tự điều khiển & ký tự ẩn
    cleaned = remove_control_characters(text)

    # Bước 2: Chuẩn hóa Unicode tiếng Việt (NFKC)
    cleaned = normalize_unicode(cleaned)

    # Bước 3: Nối từ bị gắt dòng
    cleaned = fix_hyphenated_linebreaks(cleaned)

    # Bước 4: Chuẩn hóa bullet points của danh sách kỹ năng / kinh nghiệm
    cleaned = normalize_bullet_points(cleaned)

    # Bước 5: Chuẩn hóa đường kẻ phân cách
    cleaned = normalize_separators(cleaned)

    # Bước 6: Làm sạch khoảng trắng và dòng trống dư thừa
    cleaned = clean_whitespace_and_newlines(cleaned, max_consecutive_newlines=2)

    logger.debug(
        f"[TextCleaner] Đã làm sạch CV: độ dài gốc {len(text)} -> độ dài sau làm sạch {len(cleaned)}"
    )
    return cleaned

