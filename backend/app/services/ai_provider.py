"""
services/ai_provider.py — Cơ chế chuyển đổi nhà cung cấp AI qua biến môi trường AI_PROVIDER

    cloud — chỉ dùng Google Gemini (có chuỗi model dự phòng GEMINI_FALLBACK_MODELS).
    local — chỉ dùng Ollama cục bộ (qwen2.5:7b trên GPU): offline, không giới hạn lượt gọi.
    auto  — Gemini trước; khi mọi model Gemini đều lỗi / hết hạn mức / mất mạng thì chuyển sang Ollama.

Các service nghiệp vụ (cv_extractor, sinh câu hỏi phỏng vấn...) chỉ gọi generate_structured() ở đây,
không phụ thuộc trực tiếp vào nhà cung cấp cụ thể.
"""

import logging
from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel

from app.core.config import AI_PROVIDER
from app.services import gemini_service, ollama_service
from app.services.ai_errors import AIProviderError, StructuredResult
from app.services.gemini_service import GeminiServiceError
from app.services.ollama_service import OllamaServiceError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

VALID_PROVIDERS = ("cloud", "local", "auto")


def get_provider_mode(mode: Optional[str] = None) -> str:
    """Chế độ đang dùng; giá trị không hợp lệ được coi là 'auto' (kèm cảnh báo)."""
    value = (mode or AI_PROVIDER or "auto").strip().lower()
    if value not in VALID_PROVIDERS:
        logger.warning(f"[AIProvider] AI_PROVIDER='{value}' không hợp lệ (cloud|local|auto), dùng 'auto'.")
        return "auto"
    return value


def generate_structured(
    prompt: str,
    schema: Type[T],
    system_instruction: Optional[str] = None,
    mode: Optional[str] = None,
) -> StructuredResult[T]:
    """
    Sinh JSON có cấu trúc theo `schema` bằng nhà cung cấp được cấu hình.

    Trả về:
        StructuredResult (dữ liệu + provider/model đã dùng + nhật ký các lần thử).

    Ngoại lệ:
        AIProviderError (hoặc lớp con GeminiServiceError / OllamaServiceError):
            mọi nhà cung cấp trong chế độ hiện tại đều thất bại.
        ValueError: prompt rỗng.
    """
    mode = get_provider_mode(mode)

    if mode == "cloud":
        return gemini_service.generate_structured_detailed(prompt, schema, system_instruction)
    if mode == "local":
        return ollama_service.generate_structured_detailed(prompt, schema, system_instruction)

    # auto: Gemini → Ollama
    try:
        return gemini_service.generate_structured_detailed(prompt, schema, system_instruction)
    except GeminiServiceError as gemini_error:
        logger.warning(f"[AIProvider] Gemini không dùng được ({type(gemini_error).__name__}), chuyển sang Ollama cục bộ.")
        try:
            result = ollama_service.generate_structured_detailed(prompt, schema, system_instruction)
        except OllamaServiceError as ollama_error:
            logger.error(f"[AIProvider] Ollama cũng lỗi: {ollama_error}")
            raise AIProviderError(
                f"Mọi nhà cung cấp AI đều lỗi. Gemini: {gemini_error} | Ollama: {ollama_error}"
            ) from ollama_error
        result.attempts = [f"gemini: {type(gemini_error).__name__}", *result.attempts]
        return result


def get_provider_status() -> Dict[str, Any]:
    """Trạng thái các nhà cung cấp AI (hiển thị ở /health)."""
    mode = get_provider_mode()
    status: Dict[str, Any] = {"mode": mode}
    if mode in ("cloud", "auto"):
        status["gemini"] = {
            "model_chain": gemini_service.get_model_chain(),
            "exhausted_models": gemini_service.get_exhausted_models(),
        }
    if mode in ("local", "auto"):
        status["ollama"] = ollama_service.check_ollama_status()
    return status


def preload_local_model() -> bool:
    """Chế độ local: nạp sẵn model Ollama vào GPU khi khởi động server."""
    if get_provider_mode() == "local":
        return ollama_service.preload_ollama_model()
    return False


__all__: List[str] = [
    "AIProviderError",
    "StructuredResult",
    "VALID_PROVIDERS",
    "generate_structured",
    "get_provider_mode",
    "get_provider_status",
    "preload_local_model",
]
