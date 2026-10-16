"""
services/ai_errors.py — Exception và kiểu kết quả dùng chung cho mọi nhà cung cấp AI (Gemini, Ollama)

Tách riêng để gemini_service, ollama_service và ai_provider cùng dùng mà không bị import vòng.
"""
from dataclasses import dataclass, field
from typing import Generic, List, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class AIProviderError(Exception):
    """Exception cơ sở cho lỗi của mọi nhà cung cấp AI sinh nội dung."""
    pass


@dataclass
class StructuredResult(Generic[T]):
    """Kết quả Structured Outputs kèm thông tin nguồn sinh (lưu vào CSDL để truy vết)."""

    data: T
    provider: str                 # "gemini" | "ollama"
    model: str                    # Tên model thực sự trả kết quả
    latency_seconds: float
    attempts: List[str] = field(default_factory=list)  # Nhật ký các lần thử, VD: "gemini-3.8-flash: 503"

    def meta(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "latency_seconds": round(self.latency_seconds, 2),
            "attempts": self.attempts,
        }
