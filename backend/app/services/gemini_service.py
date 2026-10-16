"""
services/gemini_service.py — Tích hợp Google Gemini API (Flash model) với chế độ Structured Outputs

Cung cấp client Gemini dùng chung (lazy singleton), hàm sinh nội dung trả về JSON
được ràng buộc theo Pydantic schema (response_schema) và các exception chuẩn hóa.

Chịu lỗi (xem docs/Issues/01, 02):
- Chuỗi model dự phòng: GEMINI_MODEL → GEMINI_FALLBACK_MODELS. Mỗi model Gemini có hạn mức miễn phí riêng.
- 503/504/5xx, lỗi mạng: thử lại cùng model GEMINI_MAX_RETRIES lần rồi chuyển model kế tiếp.
- 429 hết hạn mức theo phút: chờ đúng thời gian Google gợi ý (tối đa 30s) rồi thử lại.
- 429 hết hạn mức theo ngày: chuyển model ngay, không thử lại vô ích; ghi nhớ model đã hết lượt
  đến khi hạn mức được làm mới để các hồ sơ sau bỏ qua luôn.
- 404 (model không còn khả dụng): đánh dấu bỏ qua 24 giờ, chuyển model.
- 400/401/403 (sai key, request sai): dừng ngay vì đổi model cũng không khắc phục được.
"""

import logging
import re
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import (
    GEMINI_API_KEY,
    GEMINI_FALLBACK_MODELS,
    GEMINI_MAX_RETRIES,
    GEMINI_MODEL,
    GEMINI_TEMPERATURE,
    GEMINI_TIMEOUT_SECONDS,
)
from app.services.ai_errors import AIProviderError, StructuredResult

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Lỗi tạm thời phía máy chủ: thử lại cùng model rồi chuyển model
_RETRYABLE_STATUS_CODES = {408, 500, 502, 503, 504}
# Model không còn khả dụng (VD: "gemini-2.5-flash is no longer available to new users")
_MODEL_UNAVAILABLE_STATUS_CODES = {404}
# Chờ tối đa bao lâu cho hạn mức theo phút; lâu hơn coi như hết lượt và chuyển model
MAX_RATE_LIMIT_WAIT_SECONDS = 30.0
DEFAULT_EXHAUSTED_SECONDS = 24 * 3600


# ── Định nghĩa các Exception tùy chỉnh ──────────────────────────────────────────
class GeminiServiceError(AIProviderError):
    """Exception cơ sở cho các lỗi khi gọi Google Gemini API."""
    pass


class GeminiConfigError(GeminiServiceError):
    """Lỗi cấu hình: thiếu GEMINI_API_KEY hoặc chưa cài thư viện google-genai."""
    pass


class GeminiAPIError(GeminiServiceError):
    """Lỗi phía API Gemini (sai key, máy chủ lỗi...) sau khi đã thử hết các model."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class GeminiQuotaExhaustedError(GeminiAPIError):
    """Mọi model trong chuỗi dự phòng đều đã hết hạn mức (429 RESOURCE_EXHAUSTED)."""
    pass


class GeminiResponseError(GeminiServiceError):
    """Lỗi khi phản hồi rỗng, bị chặn bởi bộ lọc an toàn hoặc JSON không khớp schema."""
    pass


class _SwitchModel(Exception):
    """Tín hiệu nội bộ: model hiện tại không dùng được, chuyển sang model kế tiếp."""

    def __init__(self, error: Exception, status_code: Optional[int], quota: bool):
        super().__init__(str(error))
        self.error = error
        self.status_code = status_code
        self.quota = quota


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
    logger.info(f"[GeminiService] Đã khởi tạo Gemini client, chuỗi model: {get_model_chain()}.")
    return _client


def reset_gemini_client() -> None:
    """Xóa client đã cache (dùng khi đổi cấu hình hoặc trong unit test)."""
    global _client
    _client = None


# ── Quản lý chuỗi model & model đã hết hạn mức ─────────────────────────────────
_exhausted_until: Dict[str, float] = {}
_exhausted_lock = threading.Lock()


def get_model_chain(model: Optional[str] = None) -> List[str]:
    """Chuỗi model sẽ thử: model chỉ định (không dự phòng) hoặc GEMINI_MODEL + GEMINI_FALLBACK_MODELS."""
    if model:
        return [model]
    chain: List[str] = []
    for name in [GEMINI_MODEL, *GEMINI_FALLBACK_MODELS]:
        if name and name not in chain:
            chain.append(name)
    return chain


def mark_model_exhausted(model: str, seconds: float, reason: str) -> None:
    with _exhausted_lock:
        _exhausted_until[model] = time.time() + seconds
    logger.warning(
        f"[GeminiService] Tạm bỏ qua model '{model}' trong {seconds / 3600:.1f} giờ ({reason})."
    )


def is_model_exhausted(model: str) -> bool:
    with _exhausted_lock:
        until = _exhausted_until.get(model)
        if until is None:
            return False
        if until <= time.time():
            del _exhausted_until[model]
            return False
        return True


def get_exhausted_models() -> Dict[str, str]:
    """{model: thời điểm dùng lại được} — hiển thị ở /health."""
    with _exhausted_lock:
        now = time.time()
        return {
            name: datetime.fromtimestamp(until).isoformat(timespec="minutes")
            for name, until in _exhausted_until.items()
            if until > now
        }


def reset_model_state() -> None:
    """Xóa danh sách model đã hết hạn mức (dùng trong unit test)."""
    with _exhausted_lock:
        _exhausted_until.clear()


def parse_quota_error(error: Any) -> Tuple[bool, Optional[float]]:
    """
    Đọc chi tiết lỗi 429 của Gemini:
        - QuotaFailure.violations[].quotaId chứa "PerDay" → hết hạn mức theo ngày.
        - RetryInfo.retryDelay ("70290s", "19.5s") → số giây cần chờ.
    Trả về (is_daily, retry_delay_seconds).
    """
    payload = getattr(error, "details", None)
    if isinstance(payload, list) and payload:
        payload = payload[0]
    if not isinstance(payload, dict):
        return False, None
    err = payload.get("error", payload)
    is_daily = False
    retry_delay = None
    for detail in err.get("details") or []:
        if not isinstance(detail, dict):
            continue
        detail_type = str(detail.get("@type", ""))
        if detail_type.endswith("QuotaFailure"):
            for violation in detail.get("violations") or []:
                if "perday" in str(violation.get("quotaId", "")).lower():
                    is_daily = True
        elif detail_type.endswith("RetryInfo"):
            match = re.match(r"^\s*([\d.]+)s\s*$", str(detail.get("retryDelay", "")))
            if match:
                retry_delay = float(match.group(1))
    return is_daily, retry_delay


# ── Hàm sinh nội dung Structured Outputs ─────────────────────────────────────
def generate_structured(
    prompt: str,
    schema: Type[T],
    system_instruction: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_retries: Optional[int] = None,
) -> T:
    """Như generate_structured_detailed nhưng chỉ trả về dữ liệu đã validate."""
    return generate_structured_detailed(
        prompt, schema, system_instruction, model, temperature, max_retries
    ).data


def generate_structured_detailed(
    prompt: str,
    schema: Type[T],
    system_instruction: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_retries: Optional[int] = None,
) -> StructuredResult[T]:
    """
    Gọi Gemini ở chế độ Structured Outputs: ép mô hình trả về JSON đúng cấu trúc
    của Pydantic `schema` (response_mime_type="application/json" + response_schema),
    lần lượt thử các model trong chuỗi dự phòng.

    Tham số:
        prompt: Nội dung yêu cầu gửi cho mô hình.
        schema: Lớp Pydantic mô tả cấu trúc JSON đầu ra mong muốn.
        system_instruction: Chỉ dẫn hệ thống (vai trò, quy tắc) cho mô hình.
        model: Chỉ dùng đúng model này (không dự phòng). Mặc định dùng chuỗi GEMINI_MODEL + GEMINI_FALLBACK_MODELS.
        temperature: Độ sáng tạo, mặc định GEMINI_TEMPERATURE (thấp để kết quả ổn định).
        max_retries: Số lần thử lại mỗi model khi gặp lỗi tạm thời, mặc định GEMINI_MAX_RETRIES.

    Trả về:
        StructuredResult gồm dữ liệu đã validate, model đã trả kết quả và nhật ký các lần thử.

    Ngoại lệ:
        GeminiConfigError: Thiếu cấu hình.
        GeminiQuotaExhaustedError: Mọi model đều hết hạn mức.
        GeminiAPIError: API lỗi ở mọi model, hoặc lỗi không thể khắc phục (400/401/403).
        GeminiResponseError: Phản hồi rỗng / bị chặn / JSON sai schema.
    """
    if not prompt or not prompt.strip():
        raise ValueError("Prompt gửi tới Gemini không được rỗng.")

    from google.genai import types

    client = get_gemini_client()
    retries = GEMINI_MAX_RETRIES if max_retries is None else max_retries
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=GEMINI_TEMPERATURE if temperature is None else temperature,
        response_mime_type="application/json",
        response_schema=schema,
    )

    started = time.perf_counter()
    attempts: List[str] = []
    last_switch: Optional[_SwitchModel] = None
    all_quota = True
    for model_name in get_model_chain(model):
        if is_model_exhausted(model_name):
            attempts.append(f"{model_name}: bỏ qua (đang hết hạn mức)")
            continue
        try:
            data = _call_model(client, model_name, prompt, schema, config, retries, attempts)
        except _SwitchModel as switch:
            last_switch = switch
            all_quota = all_quota and switch.quota
            continue
        elapsed = time.perf_counter() - started
        logger.info(
            f"[GeminiService] '{model_name}' trả kết quả sau {elapsed:.2f}s (schema={schema.__name__})."
        )
        return StructuredResult(data, "gemini", model_name, elapsed, attempts)

    summary = "; ".join(attempts) or "không có model nào trong chuỗi"
    if all_quota:
        logger.error(f"[GeminiService] Mọi model Gemini đều hết hạn mức: {summary}")
        raise GeminiQuotaExhaustedError(f"Mọi model Gemini đều hết hạn mức: {summary}", status_code=429)
    status = last_switch.status_code if last_switch else None
    logger.error(f"[GeminiService] Mọi model Gemini đều lỗi: {summary}")
    raise GeminiAPIError(f"Mọi model Gemini đều lỗi: {summary}", status_code=status) from (
        last_switch.error if last_switch else None
    )


def _call_model(client, model_name: str, prompt: str, schema: Type[T], config, retries: int, attempts: List[str]) -> T:
    """Gọi một model, thử lại khi lỗi tạm thời; ném _SwitchModel khi cần chuyển model."""
    from google.genai import errors

    attempt = 0
    while True:
        try:
            response = client.models.generate_content(model=model_name, contents=prompt, config=config)
            data = _parse_response(response, schema)
            attempts.append(f"{model_name}: OK")
            return data

        except errors.APIError as e:
            status = getattr(e, "code", None)

            if status == 429:
                is_daily, delay = parse_quota_error(e)
                if is_daily or (delay is not None and delay > MAX_RATE_LIMIT_WAIT_SECONDS):
                    mark_model_exhausted(
                        model_name, delay or DEFAULT_EXHAUSTED_SECONDS,
                        "hết hạn mức theo ngày" if is_daily else f"cần chờ {delay:.0f}s",
                    )
                    attempts.append(f"{model_name}: 429 hết hạn mức{' theo ngày' if is_daily else ''}")
                    raise _SwitchModel(e, status, quota=True)
                if attempt < retries:
                    wait = delay if delay is not None else 2 ** attempt
                    attempt += 1
                    logger.warning(
                        f"[GeminiService] '{model_name}' hết hạn mức theo phút (429), chờ {wait:.0f}s rồi thử lại "
                        f"lần {attempt}/{retries}..."
                    )
                    time.sleep(wait)
                    continue
                attempts.append(f"{model_name}: 429")
                raise _SwitchModel(e, status, quota=True)

            if status in _MODEL_UNAVAILABLE_STATUS_CODES:
                mark_model_exhausted(model_name, DEFAULT_EXHAUSTED_SECONDS, "model không khả dụng (404)")
                attempts.append(f"{model_name}: 404 không khả dụng")
                raise _SwitchModel(e, status, quota=False)

            if status in _RETRYABLE_STATUS_CODES:
                if attempt < retries:
                    delay = 2 ** attempt
                    attempt += 1
                    logger.warning(
                        f"[GeminiService] Lỗi tạm thời {status} từ '{model_name}', thử lại lần {attempt}/{retries} "
                        f"sau {delay}s..."
                    )
                    time.sleep(delay)
                    continue
                attempts.append(f"{model_name}: {status}")
                logger.warning(f"[GeminiService] '{model_name}' vẫn lỗi {status}, chuyển model dự phòng.")
                raise _SwitchModel(e, status, quota=False)

            logger.error(f"[GeminiService] Gemini API lỗi {status} (không thể khắc phục bằng đổi model): {e}")
            raise GeminiAPIError(f"Gemini API lỗi ({status}): {e}", status_code=status) from e

        except httpx.TransportError as e:
            # Lỗi mạng / timeout: thử lại như lỗi tạm thời rồi chuyển model
            if attempt < retries:
                delay = 2 ** attempt
                attempt += 1
                logger.warning(
                    f"[GeminiService] Lỗi kết nối tới '{model_name}' ({type(e).__name__}), thử lại lần "
                    f"{attempt}/{retries} sau {delay}s..."
                )
                time.sleep(delay)
                continue
            attempts.append(f"{model_name}: lỗi kết nối ({type(e).__name__})")
            raise _SwitchModel(e, None, quota=False)


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
