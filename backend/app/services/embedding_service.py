"""
services/embedding_service.py — Tải và cấu hình mô hình nhúng sentence-transformers chạy cục bộ (CPU)

Mô hình mặc định: paraphrase-multilingual-MiniLM-L12-v2
- Hỗ trợ hơn 50 ngôn ngữ (gồm tiếng Việt & tiếng Anh) → so khớp CV/JD viết lẫn 2 ngôn ngữ.
- Vector 384 chiều, ~118M tham số (~470MB), chạy tốt trên CPU.
- Giới hạn 128 token mỗi đoạn → văn bản dài được chia nhỏ (chunk) rồi lấy trung bình vector.

Mô hình được nạp một lần (lazy singleton, an toàn đa luồng vì BackgroundTasks chạy trong threadpool)
và cache trong thư mục EMBEDDING_CACHE_DIR để các lần sau chạy được cả khi ngắt mạng.
"""

import logging
import re
import threading
import time
from pathlib import Path
from typing import List, Optional, Sequence

import numpy as np

from app.core.config import (
    BASE_DIR,
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_CACHE_DIR,
    EMBEDDING_DEVICE,
    EMBEDDING_MODEL_NAME,
)

logger = logging.getLogger(__name__)

# Số từ tối đa mỗi đoạn: ~128 token của tokenizer ≈ 80-90 từ tiếng Việt/Anh
DEFAULT_CHUNK_WORDS = 80
DEFAULT_CHUNK_OVERLAP = 15


# ── Định nghĩa các Exception tùy chỉnh ──────────────────────────────────────────
class EmbeddingServiceError(Exception):
    """Exception cơ sở cho các lỗi của service nhúng vector."""
    pass


class EmbeddingModelLoadError(EmbeddingServiceError):
    """Lỗi khi không thể tải/nạp mô hình (chưa cài thư viện, chưa tải model khi offline...)."""
    pass


# ── Nạp mô hình dùng chung ────────────────────────────────────────────────────
_model = None
_model_lock = threading.Lock()


def get_cache_dir() -> Path:
    """Đường dẫn tuyệt đối tới thư mục cache mô hình."""
    path = Path(EMBEDDING_CACHE_DIR)
    if not path.is_absolute():
        path = BASE_DIR / path
    return path


def get_embedding_model():
    """
    Nạp (một lần) và trả về SentenceTransformer dùng chung.
    Lần đầu sẽ tải mô hình từ Hugging Face về EMBEDDING_CACHE_DIR; các lần sau đọc từ cache.

    Ngoại lệ:
        EmbeddingModelLoadError: Chưa cài sentence-transformers hoặc không tải được mô hình.
    """
    global _model
    if _model is not None:
        return _model

    with _model_lock:
        if _model is not None:  # Luồng khác đã nạp xong trong lúc chờ lock
            return _model

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise EmbeddingModelLoadError(
                "Chưa cài thư viện sentence-transformers. Chạy: pip install -r requirements.txt"
            ) from e

        cache_dir = get_cache_dir()
        cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            f"[EmbeddingService] Đang nạp mô hình '{EMBEDDING_MODEL_NAME}' trên '{EMBEDDING_DEVICE}' "
            f"(cache: {cache_dir})..."
        )
        started = time.perf_counter()
        try:
            _model = SentenceTransformer(
                EMBEDDING_MODEL_NAME,
                device=EMBEDDING_DEVICE,
                cache_folder=str(cache_dir),
            )
        except Exception as e:
            logger.error(f"[EmbeddingService] Không thể nạp mô hình nhúng: {e}")
            raise EmbeddingModelLoadError(
                f"Không thể nạp mô hình '{EMBEDDING_MODEL_NAME}'. "
                f"Nếu đang offline, hãy chạy trước: python download_embedding_model.py. Chi tiết: {e}"
            ) from e

        logger.info(
            f"[EmbeddingService] Đã nạp mô hình sau {time.perf_counter() - started:.1f}s "
            f"(dim={get_embedding_dimension(_model)}, max_seq_length={_model.max_seq_length})."
        )
        return _model


def get_embedding_dimension(model=None) -> int:
    """Số chiều vector của mô hình (384 với MiniLM-L12-v2)."""
    model = model or get_embedding_model()
    getter = getattr(model, "get_embedding_dimension", None) or model.get_sentence_embedding_dimension
    return int(getter())


def is_model_loaded() -> bool:
    return _model is not None


def reset_embedding_model() -> None:
    """Giải phóng mô hình đã nạp (dùng khi đổi cấu hình hoặc trong unit test)."""
    global _model
    with _model_lock:
        _model = None


def preload_embedding_model() -> bool:
    """
    Nạp sẵn mô hình khi khởi động server. Không ném lỗi để server vẫn chạy được
    các chức năng khác nếu mô hình chưa sẵn sàng.
    """
    try:
        model = get_embedding_model()
        model.encode(["warm-up"], show_progress_bar=False)  # Khởi động kernel lần đầu
        return True
    except EmbeddingServiceError as e:
        logger.warning(f"[EmbeddingService] Bỏ qua nạp sẵn mô hình nhúng: {e}")
        return False


# ── Chia đoạn & mã hóa vector ─────────────────────────────────────────────────
def split_into_chunks(
    text: str,
    max_words: int = DEFAULT_CHUNK_WORDS,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[str]:
    """
    Chia văn bản dài thành các đoạn ≤ max_words từ (gối đầu `overlap` từ) để không bị
    mô hình cắt cụt ở 128 token. Văn bản ngắn trả về nguyên một đoạn.
    """
    if overlap >= max_words:
        raise ValueError("overlap phải nhỏ hơn max_words")
    words = re.split(r"\s+", (text or "").strip())
    words = [w for w in words if w]
    if not words:
        return []
    if len(words) <= max_words:
        return [" ".join(words)]

    chunks = []
    step = max_words - overlap
    for start in range(0, len(words), step):
        chunks.append(" ".join(words[start:start + max_words]))
        if start + max_words >= len(words):
            break
    return chunks


def encode_texts(
    texts: Sequence[str],
    normalize: bool = True,
    batch_size: Optional[int] = None,
) -> np.ndarray:
    """
    Mã hóa danh sách câu/đoạn ngắn thành ma trận vector shape (n, dim), dtype float32.
    normalize=True chuẩn hóa L2 → cosine similarity = tích vô hướng.
    """
    if not texts:
        raise ValueError("Danh sách văn bản cần mã hóa rỗng.")
    model = get_embedding_model()
    vectors = model.encode(
        list(texts),
        batch_size=batch_size or EMBEDDING_BATCH_SIZE,
        normalize_embeddings=normalize,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return np.asarray(vectors, dtype=np.float32)


def encode_document(text: str, normalize: bool = True) -> np.ndarray:
    """
    Mã hóa một văn bản dài (CV hoặc JD) thành 1 vector duy nhất shape (dim,):
    chia đoạn → mã hóa từng đoạn → trung bình cộng → chuẩn hóa L2.
    """
    chunks = split_into_chunks(text)
    if not chunks:
        raise ValueError("Văn bản cần mã hóa rỗng.")
    chunk_vectors = encode_texts(chunks, normalize=True)
    doc_vector = chunk_vectors.mean(axis=0)
    if normalize:
        norm = np.linalg.norm(doc_vector)
        if norm > 0:
            doc_vector = doc_vector / norm
    return doc_vector.astype(np.float32)
