"""
services/gemini_service.py — Tích hợp Google Gemini API (Flash model) với chế độ Structured Outputs

Cung cấp client Gemini dùng chung (lazy singleton), hàm sinh nội dung trả về JSON
được ràng buộc theo Pydantic schema (response_schema), cơ chế retry cho lỗi tạm thời
(429 / 5xx) và các exception chuẩn hóa để tầng AI Pipeline xử lý thống nhất.
"""

import logging
import time
from typing import Optional, Type, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import (
    GEMINI_API_KEY,
    GEMINI_MAX_RETRIES,
    GEMINI_MODEL,
    GEMINI_TEMPERATURE,
    GEMINI_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Mã HTTP được coi là lỗi tạm thời, có thể thử lại
_RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


# ── Định nghĩa các Exception tùy chỉnh ──────────────────────────────────────────
class GeminiServiceError(Exception):
    """Exception cơ sở cho các lỗi khi gọi Google Gemini API."""
    pass


class GeminiConfigError(GeminiServiceError):
    """Lỗi cấu hình: thiếu GEMINI_API_KEY hoặc chưa cài thư viện google-genai."""
    pass


class GeminiAPIError(GeminiServiceError):
    """Lỗi phía API Gemini (sai key, hết quota, máy chủ lỗi...) sau khi đã retry."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class GeminiResponseError(GeminiServiceError):
    """Lỗi khi phản hồi rỗng, bị chặn bởi bộ lọc an toàn hoặc JSON không khớp schema."""
    pass


# ── Client dùng chung ─────────────────────────────────────────────────────────
_client = None


def get_gemini_client():
    """
    Khởi tạo (một lần) và trả về genai.Client dùng chung cho toàn ứng dụng.

    Ngoại lệ:
        GeminiConfigError: Thiếu API key hoặc chưa cài google-genai.
    """
    global _client
    if _client is not None:
        return _client

    if not GEMINI_API_KEY:
        raise GeminiConfigError("Chưa cấu hình GEMINI_API_KEY trong file .env")

    try:
        from google import genai
        from google.genai import types
    except ImportError as e:
        raise GeminiConfigError(
            "Chưa cài thư viện google-genai. Chạy: pip install google-genai"
        ) from e

    _client = genai.Client(
        api_key=GEMINI_API_KEY,
        http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_SECONDS * 1000),
    )
    logger.info(f"[GeminiService] Đã khởi tạo Gemini client với model '{GEMINI_MODEL}'.")
    return _client


def reset_gemini_client() -> None:
    """Xóa client đã cache (dùng khi đổi cấu hình hoặc trong unit test)."""
    global _client
    _client = None


# ── Hàm sinh nội dung Structured Outputs ─────────────────────────────────────
def generate_structured(
    prompt: str,
    schema: Type[T],
    system_instruction: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_retries: Optional[int] = None,
) -> T:
    """
    Gọi Gemini ở chế độ Structured Outputs: ép mô hình trả về JSON đúng cấu trúc
    của Pydantic `schema` (response_mime_type="application/json" + response_schema).

    Tham số:
        prompt: Nội dung yêu cầu gửi cho mô hình.
        schema: Lớp Pydantic mô tả cấu trúc JSON đầu ra mong muốn.
        system_instruction: Chỉ dẫn hệ thống (vai trò, quy tắc) cho mô hình.
        model: Tên model, mặc định lấy GEMINI_MODEL từ .env.
        temperature: Độ sáng tạo, mặc định GEMINI_TEMPERATURE (thấp để kết quả ổn định).
        max_retries: Số lần thử lại khi gặp lỗi tạm thời (429/5xx), mặc định GEMINI_MAX_RETRIES.

    Trả về:
        Instance của `schema` đã được validate.

    Ngoại lệ:
        GeminiConfigError: Thiếu cấu hình.
        GeminiAPIError: API lỗi sau khi đã hết số lần retry.
        GeminiResponseError: Phản hồi rỗng / bị chặn / JSON sai schema.
    """
    if not prompt or not prompt.strip():
        raise ValueError("Prompt gửi tới Gemini không được rỗng.")

    from google.genai import errors, types

    client = get_gemini_client()
    model_name = model or GEMINI_MODEL
    retries = GEMINI_MAX_RETRIES if max_retries is None else max_retries

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=GEMINI_TEMPERATURE if temperature is None else temperature,
        response_mime_type="application/json",
        response_schema=schema,
    )

    attempt = 0
    while True:
        try:
            started = time.perf_counter()
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            elapsed = time.perf_counter() - started
            logger.info(
                f"[GeminiService] Gọi '{model_name}' thành công sau {elapsed:.2f}s "
                f"(schema={schema.__name__}, lần thử {attempt + 1})."
            )
            return _parse_response(response, schema)

        except errors.APIError as e:
            status = getattr(e, "code", None)
            if status in _RETRYABLE_STATUS_CODES and attempt < retries:
                delay = 2 ** attempt
                attempt += 1
                logger.warning(
                    f"[GeminiService] Lỗi tạm thời {status} từ Gemini, thử lại lần {attempt}/{retries} sau {delay}s..."
                )
                time.sleep(delay)
                continue
            logger.error(f"[GeminiService] Gemini API lỗi {status}: {e}")
            raise GeminiAPIError(f"Gemini API lỗi ({status}): {e}", status_code=status) from e

        except httpx.TransportError as e:
            # Lỗi mạng / timeout: cũng thử lại như lỗi tạm thời
            if attempt < retries:
                delay = 2 ** attempt
                attempt += 1
                logger.warning(
                    f"[GeminiService] Lỗi kết nối tới Gemini ({type(e).__name__}), thử lại lần {attempt}/{retries} sau {delay}s..."
                )
                time.sleep(delay)
                continue
            logger.error(f"[GeminiService] Không thể kết nối tới Gemini: {e}")
            raise GeminiAPIError(f"Không thể kết nối tới Gemini: {e}") from e


def _parse_response(response, schema: Type[T]) -> T:
    """
    Chuyển phản hồi Gemini về instance Pydantic.
    Ưu tiên `response.parsed` (SDK tự parse theo schema), dự phòng validate từ `response.text`.
    """
    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, schema):
        return parsed

    text = getattr(response, "text", None)
    if not text or not text.strip():
        reason = _get_block_reason(response)
        raise GeminiResponseError(
            f"Gemini trả về phản hồi rỗng{f' (lý do: {reason})' if reason else ''}."
        )

    try:
        return schema.model_validate_json(text)
    except ValidationError as e:
        logger.error(f"[GeminiService] JSON từ Gemini không khớp schema {schema.__name__}: {e}")
        raise GeminiResponseError(f"JSON trả về không khớp schema {schema.__name__}: {e}") from e


def _get_block_reason(response) -> Optional[str]:
    """Lấy lý do bị chặn/kết thúc bất thường (safety, max tokens...) nếu có."""
    feedback = getattr(response, "prompt_feedback", None)
    if feedback is not None and getattr(feedback, "block_reason", None):
        return str(feedback.block_reason)
    candidates = getattr(response, "candidates", None) or []
    if candidates and getattr(candidates[0], "finish_reason", None):
        return str(candidates[0].finish_reason)
    return None
