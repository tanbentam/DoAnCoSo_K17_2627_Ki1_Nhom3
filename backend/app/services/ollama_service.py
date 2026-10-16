"""
services/ollama_service.py — Service adapter gọi mô hình cục bộ qua Ollama (qwen2.5:7b trên GPU RTX 4060)

Cùng giao diện với gemini_service.generate_structured_detailed để tầng ai_provider hoán đổi tự do:
- Gọi POST {OLLAMA_BASE_URL}/api/chat với `format` = JSON Schema của Pydantic → Ollama ràng buộc
  đầu ra bằng grammar, mô hình chỉ có thể sinh JSON đúng cấu trúc (tương đương Structured Outputs của Gemini).
- Grammar không truyền được `description` của từng trường cho mô hình, nên schema được đưa thêm
  vào system prompt (khuyến nghị của Ollama) để mô hình hiểu ý nghĩa trường như Gemini.
- Chạy hoàn toàn offline, không giới hạn lượt gọi.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional, Type, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import (
    OLLAMA_BASE_URL,
    OLLAMA_KEEP_ALIVE,
    OLLAMA_MODEL,
    OLLAMA_NUM_CTX,
    OLLAMA_TEMPERATURE,
    OLLAMA_TIMEOUT_SECONDS,
)
from app.services.ai_errors import AIProviderError, StructuredResult

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


# ── Định nghĩa các Exception tùy chỉnh ──────────────────────────────────────────
class OllamaServiceError(AIProviderError):
    """Exception cơ sở cho các lỗi khi gọi Ollama."""
    pass


class OllamaConnectionError(OllamaServiceError):
    """Không kết nối được tới Ollama (chưa mở ứng dụng / chưa chạy `ollama serve`)."""
    pass


class OllamaModelNotFoundError(OllamaServiceError):
    """Model chưa được tải về máy (cần `ollama pull <model>`)."""
    pass


class OllamaResponseError(OllamaServiceError):
    """Phản hồi rỗng hoặc JSON không khớp schema sau khi đã thử lại."""
    pass


# ── Hàm sinh nội dung Structured Outputs ─────────────────────────────────────
def generate_structured(
    prompt: str,
    schema: Type[T],
    system_instruction: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_retries: int = 1,
) -> T:
    """Như generate_structured_detailed nhưng chỉ trả về dữ liệu đã validate."""
    return generate_structured_detailed(prompt, schema, system_instruction, model, temperature, max_retries).data


def generate_structured_detailed(
    prompt: str,
    schema: Type[T],
    system_instruction: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_retries: int = 1,
) -> StructuredResult[T]:
    """
    Gọi mô hình Ollama cục bộ, ép đầu ra theo JSON Schema của `schema`.

    Tham số:
        prompt: Nội dung yêu cầu.
        schema: Lớp Pydantic mô tả JSON đầu ra.
        system_instruction: Chỉ dẫn hệ thống (dùng chung với Gemini).
        model: Tên model Ollama, mặc định OLLAMA_MODEL.
        temperature: Mặc định OLLAMA_TEMPERATURE.
        max_retries: Số lần gọi lại khi JSON trả về không khớp schema.

    Ngoại lệ:
        OllamaConnectionError, OllamaModelNotFoundError, OllamaResponseError, OllamaServiceError.
    """
    if not prompt or not prompt.strip():
        raise ValueError("Prompt gửi tới Ollama không được rỗng.")

    model_name = model or OLLAMA_MODEL
    payload = build_chat_payload(prompt, schema, system_instruction, model_name, temperature)

    started = time.perf_counter()
    attempts: List[str] = []
    last_error: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        body = _post_chat(payload, model_name)
        content = (body.get("message") or {}).get("content") or ""
        _log_performance(body, model_name)
        if not content.strip():
            attempts.append(f"{model_name}: phản hồi rỗng")
            last_error = OllamaResponseError("Ollama trả về phản hồi rỗng.")
            continue
        try:
            data = schema.model_validate_json(content)
        except ValidationError as e:
            attempts.append(f"{model_name}: JSON sai schema")
            logger.warning(
                f"[OllamaService] JSON từ '{model_name}' không khớp schema {schema.__name__} "
                f"(lần {attempt + 1}/{max_retries + 1}): {e.error_count()} lỗi."
            )
            last_error = e
            continue
        attempts.append(f"{model_name}: OK")
        elapsed = time.perf_counter() - started
        logger.info(f"[OllamaService] '{model_name}' trả kết quả sau {elapsed:.2f}s (schema={schema.__name__}).")
        return StructuredResult(data, "ollama", model_name, elapsed, attempts)

    raise OllamaResponseError(
        f"Ollama '{model_name}' không trả về JSON hợp lệ theo schema {schema.__name__}: {last_error}"
    ) from last_error


def build_chat_payload(
    prompt: str,
    schema: Type[BaseModel],
    system_instruction: Optional[str],
    model_name: str,
    temperature: Optional[float] = None,
) -> Dict[str, Any]:
    """Tạo body cho POST /api/chat: system prompt kèm JSON Schema + format ràng buộc đầu ra."""
    json_schema = schema.model_json_schema()
    system = (
        f"{(system_instruction or '').strip()}\n\n"
        "Chỉ trả về MỘT đối tượng JSON hợp lệ theo JSON Schema dưới đây, tuân thủ mô tả (description) "
        "của từng trường:\n"
        f"{json.dumps(json_schema, ensure_ascii=False)}"
    ).strip()
    return {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "format": json_schema,
        "stream": False,
        "keep_alive": OLLAMA_KEEP_ALIVE,
        "options": {
            "temperature": OLLAMA_TEMPERATURE if temperature is None else temperature,
            "num_ctx": OLLAMA_NUM_CTX,
        },
    }


def _post_chat(payload: Dict[str, Any], model_name: str) -> Dict[str, Any]:
    url = f"{OLLAMA_BASE_URL}/api/chat"
    try:
        resp = httpx.post(url, json=payload, timeout=OLLAMA_TIMEOUT_SECONDS)
    except httpx.ConnectError as e:
        raise OllamaConnectionError(
            f"Không kết nối được Ollama tại {OLLAMA_BASE_URL}. Hãy mở ứng dụng Ollama hoặc chạy: ollama serve"
        ) from e
    except httpx.TimeoutException as e:
        raise OllamaServiceError(f"Ollama không phản hồi sau {OLLAMA_TIMEOUT_SECONDS}s.") from e
    except httpx.HTTPError as e:
        raise OllamaServiceError(f"Lỗi khi gọi Ollama: {e}") from e

    if resp.status_code == 404:
        raise OllamaModelNotFoundError(
            f"Model '{model_name}' chưa có trên máy. Chạy: ollama pull {model_name}"
        )
    if resp.status_code >= 400:
        raise OllamaServiceError(f"Ollama lỗi {resp.status_code}: {resp.text[:300]}")
    try:
        return resp.json()
    except ValueError as e:
        raise OllamaResponseError(f"Ollama trả về dữ liệu không phải JSON: {resp.text[:200]}") from e


def _log_performance(body: Dict[str, Any], model_name: str) -> None:
    """Ghi log tốc độ sinh token (tokens/s) và thời gian nạp model để theo dõi hiệu năng GPU."""
    eval_count = body.get("eval_count") or 0
    eval_ns = body.get("eval_duration") or 0
    load_s = (body.get("load_duration") or 0) / 1e9
    if eval_count and eval_ns:
        logger.info(
            f"[OllamaService] '{model_name}': {body.get('prompt_eval_count', 0)} token vào, {eval_count} token ra, "
            f"{eval_count / (eval_ns / 1e9):.1f} token/s, nạp model {load_s:.1f}s."
        )


# ── Kiểm tra trạng thái & nạp sẵn ─────────────────────────────────────────────
def check_ollama_status(timeout: float = 2.0) -> Dict[str, Any]:
    """Kiểm tra Ollama có chạy và đã có OLLAMA_MODEL chưa (dùng cho /health)."""
    status: Dict[str, Any] = {"base_url": OLLAMA_BASE_URL, "model": OLLAMA_MODEL, "reachable": False, "model_ready": False}
    try:
        resp = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=timeout)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        status["error"] = f"{type(e).__name__}: {e}"
        return status
    status["reachable"] = True
    models = resp.json().get("models", [])
    names = {m.get("name") for m in models} | {m.get("model") for m in models}
    status["model_ready"] = OLLAMA_MODEL in names or f"{OLLAMA_MODEL}:latest" in names
    return status


def preload_ollama_model() -> bool:
    """Nạp sẵn model vào VRAM (gửi request rỗng kèm keep_alive). Không ném lỗi."""
    try:
        httpx.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "keep_alive": OLLAMA_KEEP_ALIVE},
            timeout=OLLAMA_TIMEOUT_SECONDS,
        ).raise_for_status()
        logger.info(f"[OllamaService] Đã nạp sẵn '{OLLAMA_MODEL}' vào bộ nhớ GPU.")
        return True
    except httpx.HTTPError as e:
        logger.warning(f"[OllamaService] Bỏ qua nạp sẵn '{OLLAMA_MODEL}': {e}")
        return False
