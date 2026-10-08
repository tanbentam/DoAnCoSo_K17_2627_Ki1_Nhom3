"""
services/pdf_service.py — Service trích xuất văn bản thô từ file PDF CV bằng pdfplumber

Cung cấp các hàm trích xuất text, bóc tách theo từng trang, đọc metadata và
xử lý ngoại lệ chuẩn hóa (file không tồn tại, file hỏng, mã hóa/password protected).
"""

import io
import logging
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Union

import pdfplumber
from pdfminer.pdfdocument import PDFPasswordIncorrect
from pdfminer.pdfparser import PDFSyntaxError
from pdfplumber.utils.exceptions import PdfminerException

from app.core.config import BASE_DIR
from app.services.text_cleaner import clean_cv_text

logger = logging.getLogger(__name__)


# ── Định nghĩa các Exception tùy chỉnh ──────────────────────────────────────────
class PDFServiceError(Exception):
    """Exception cơ sở cho các lỗi xảy ra trong quá trình xử lý file PDF."""
    pass


class PDFFileNotFoundError(PDFServiceError):
    """Lỗi khi đường dẫn file PDF không tồn tại."""
    pass


class PDFCorruptedError(PDFServiceError):
    """Lỗi khi cấu trúc file PDF bị hỏng hoặc không đúng định dạng PDF hợp lệ."""
    pass


class PDFEncryptedError(PDFServiceError):
    """Lỗi khi file PDF bị cài mật khẩu bảo vệ không thể đọc."""
    pass


class PDFEmptyError(PDFServiceError):
    """Cảnh báo/Lỗi khi file PDF không chứa bất kỳ văn bản nào (ví dụ ảnh scan không có OCR)."""
    pass


# ── Hàm trích xuất chính ──────────────────────────────────────────────────────
def extract_text_from_pdf(
    pdf_source: Union[str, Path, bytes, BinaryIO],
    password: Optional[str] = None,
    keep_blank_chars: bool = False,
    clean: bool = False,
) -> str:
    """
    Trích xuất toàn bộ văn bản thô từ file PDF sử dụng pdfplumber.

    Tham số:
        pdf_source: Đường dẫn file (str, Path), chuỗi bytes hoặc file-like stream (BytesIO).
        password: Mật khẩu mở file nếu PDF bị khóa.
        keep_blank_chars: Giữ lại các ký tự khoảng trắng nguyên bản từ layout.
        clean: Nếu True, áp dụng bộ làm sạch clean_cv_text lên kết quả trích xuất.

    Trả về:
        str: Toàn bộ văn bản đã trích xuất từ tất cả các trang, phân cách bởi ký tự xuống dòng.

    Ngoại lệ:
        PDFFileNotFoundError: File không tìm thấy trên hệ thống.
        PDFCorruptedError: File hỏng hoặc không phải là định dạng PDF hợp lệ.
        PDFEncryptedError: File có mật khẩu bảo vệ nhưng mật khẩu không đúng hoặc chưa được cung cấp.
        PDFServiceError: Lỗi không xác định khác trong quá trình đọc PDF.
    """
    pages_text = extract_pages_text(
        pdf_source=pdf_source,
        password=password,
        keep_blank_chars=keep_blank_chars,
    )
    
    # Ghép văn bản các trang lại với nhau
    full_text = "\n\n".join(text for text in pages_text if text.strip())
    if clean:
        full_text = clean_cv_text(full_text)
    return full_text.strip()


def extract_pages_text(
    pdf_source: Union[str, Path, bytes, BinaryIO],
    password: Optional[str] = None,
    keep_blank_chars: bool = False,
) -> List[str]:
    """
    Trích xuất văn bản thô từ file PDF theo từng trang riêng biệt.

    Tham số:
        pdf_source: Đường dẫn file (str, Path), chuỗi bytes hoặc stream.
        password: Mật khẩu mở file nếu có.
        keep_blank_chars: Giữ ký tự khoảng trắng.

    Trả về:
        List[str]: Danh sách chuỗi văn bản của từng trang theo thứ tự (từ trang 1 đến hết).
    """
    stream_or_path = _resolve_pdf_source(pdf_source)
    pages_text: List[str] = []

    try:
        with pdfplumber.open(stream_or_path, password=password) as pdf:
            total_pages = len(pdf.pages)
            logger.info(f"[PDFService] Đang mở PDF thành công. Tổng số trang: {total_pages}")

            if total_pages == 0:
                logger.warning("[PDFService] File PDF không chứa trang nào.")
                return []

            for idx, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text(layout=False) or ""
                
                # Nếu trang có bảng biểu mà extract_text không lấy hết, lấy thêm text từ tables
                if not page_text.strip():
                    tables = page.extract_tables()
                    if tables:
                        table_rows = []
                        for table in tables:
                            for row in table:
                                cleaned_row = [str(cell).strip() for cell in row if cell is not None]
                                if cleaned_row:
                                    table_rows.append(" | ".join(cleaned_row))
                        page_text = "\n".join(table_rows)

                logger.debug(f"[PDFService] Trang {idx}/{total_pages}: {len(page_text)} ký tự.")
                pages_text.append(page_text)

        return pages_text

    except (PDFSyntaxError, PdfminerException) as e:
        logger.error(f"[PDFService] File PDF bị lỗi cấu trúc cú pháp: {e}")
        raise PDFCorruptedError(f"Tệp không phải là PDF hợp lệ hoặc đã bị lỗi/hỏng: {e}") from e
    except PDFPasswordIncorrect as e:
        logger.error("[PDFService] PDF có mật khẩu bảo vệ và mật khẩu cung cấp không chính xác.")
        raise PDFEncryptedError("File PDF đã bị đặt mật khẩu bảo vệ, không thể đọc.") from e
    except FileNotFoundError as e:
        raise
    except Exception as e:
        # Kiểm tra xem có phải do password không (pdfplumber đôi khi ném exception khác khi file có password)
        err_msg = str(e).lower()
        if "password" in err_msg or "encrypt" in err_msg:
            logger.error(f"[PDFService] Lỗi mật khẩu bảo vệ PDF: {e}")
            raise PDFEncryptedError(f"Tệp PDF được bảo vệ bằng mật khẩu: {e}") from e
        logger.error(f"[PDFService] Lỗi không xác định khi trích xuất PDF: {e}")
        raise PDFServiceError(f"Lỗi khi xử lý file PDF: {e}") from e


def get_pdf_metadata(
    pdf_source: Union[str, Path, bytes, BinaryIO],
    password: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Trích xuất metadata và thông tin cơ bản của file PDF (số trang, tác giả, ngày tạo...).
    """
    stream_or_path = _resolve_pdf_source(pdf_source)
    try:
        with pdfplumber.open(stream_or_path, password=password) as pdf:
            metadata: Dict[str, Any] = {
                "total_pages": len(pdf.pages),
                "metadata": pdf.metadata or {},
            }
            if isinstance(pdf_source, (str, Path)):
                file_path = _to_absolute_path(pdf_source)
                if file_path.exists():
                    metadata["file_name"] = file_path.name
                    metadata["file_size_bytes"] = file_path.stat().st_size
            return metadata
    except (PDFSyntaxError, PdfminerException) as e:
        raise PDFCorruptedError(f"Không thể đọc metadata, file PDF bị hỏng: {e}") from e
    except Exception as e:
        raise PDFServiceError(f"Lỗi khi đọc metadata PDF: {e}") from e


def extract_text_from_candidate_cv(
    cv_relative_or_absolute_path: Union[str, Path],
    clean: bool = True,
) -> str:
    """
    Helper chuyên biệt để trích xuất văn bản từ đường dẫn CV ứng viên lưu trong hệ thống.
    Tự động chuẩn hóa đường dẫn tương đối (ví dụ: uploads/cv/abc.pdf) về đường dẫn tuyệt đối dựa trên BASE_DIR.

    Tham số:
        cv_relative_or_absolute_path: Đường dẫn tới file CV (tương đối hoặc tuyệt đối).
        clean: Có áp dụng bộ làm sạch clean_cv_text hay không (mặc định True).

    Trả về:
        str: Toàn bộ nội dung văn bản CV đã được trích xuất (và làm sạch nếu clean=True).
    """
    abs_path = _to_absolute_path(cv_relative_or_absolute_path)
    if not abs_path.exists():
        raise PDFFileNotFoundError(f"Không tìm thấy file CV tại đường dẫn: {abs_path}")

    ext = abs_path.suffix.lower()
    if ext != ".pdf":
        raise PDFServiceError(f"Định dạng tệp {ext} không được hỗ trợ bởi PDF service. Chỉ hỗ trợ .pdf")

    return extract_text_from_pdf(abs_path, clean=clean)


# ── Hàm bổ trợ nội bộ ────────────────────────────────────────────────────────
def _to_absolute_path(path_input: Union[str, Path]) -> Path:
    """Chuyển đổi đường dẫn tương đối về đường dẫn tuyệt đối theo BASE_DIR."""
    path_obj = Path(path_input)
    if not path_obj.is_absolute():
        path_obj = BASE_DIR / path_obj
    return path_obj


def _resolve_pdf_source(pdf_source: Union[str, Path, bytes, BinaryIO]) -> Union[str, BinaryIO]:
    """
    Chuẩn hóa nguồn PDF đầu vào thành dạng pdfplumber có thể đọc:
    - Nếu là str hoặc Path: kiểm tra file tồn tại và trả về str đường dẫn tuyệt đối.
    - Nếu là bytes: bọc trong io.BytesIO.
    - Nếu là stream: giữ nguyên.
    """
    if isinstance(pdf_source, (str, Path)):
        abs_path = _to_absolute_path(pdf_source)
        if not abs_path.exists():
            logger.error(f"[PDFService] File không tồn tại: {abs_path}")
            raise PDFFileNotFoundError(f"File PDF không tồn tại: {abs_path}")
        return str(abs_path)
    elif isinstance(pdf_source, bytes):
        return io.BytesIO(pdf_source)
    elif hasattr(pdf_source, "read"):
        return pdf_source
    else:
        raise PDFServiceError(f"Kiểu dữ liệu đầu vào không được hỗ trợ: {type(pdf_source)}")

