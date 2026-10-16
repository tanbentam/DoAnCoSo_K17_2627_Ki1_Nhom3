# app/services/__init__.py
from app.services.ai_errors import AIProviderError, StructuredResult
from app.services.ai_provider import (
    generate_structured,
    get_provider_mode,
    get_provider_status,
)
from app.services.cv_extractor import (
    CV_EXTRACTION_SYSTEM_INSTRUCTION,
    build_cv_extraction_prompt,
    extract_cv_info,
    extract_cv_info_detailed,
    normalize_cv_extraction,
)
from app.services.embedding_service import (
    EmbeddingModelLoadError,
    EmbeddingServiceError,
    encode_document,
    encode_texts,
    get_embedding_model,
    preload_embedding_model,
    split_into_chunks,
)
from app.services.gemini_service import (
    GeminiAPIError,
    GeminiConfigError,
    GeminiQuotaExhaustedError,
    GeminiResponseError,
    GeminiServiceError,
    get_gemini_client,
)
from app.services.hybrid_scoring import (
    HardFilterResult,
    HybridScoreResult,
    SkillMatch,
    combine_scores,
    compute_hard_filter,
    compute_hybrid_score,
    match_skills,
    normalize_skill,
)
from app.services.ollama_service import (
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaResponseError,
    OllamaServiceError,
    check_ollama_status,
)
from app.services.pdf_service import (
    PDFCorruptedError,
    PDFEmptyError,
    PDFEncryptedError,
    PDFFileNotFoundError,
    PDFServiceError,
    extract_pages_text,
    extract_text_from_candidate_cv,
    extract_text_from_pdf,
    get_pdf_metadata,
)
from app.services.semantic_matching import (
    SemanticMatchResult,
    build_job_text,
    compute_job_cv_match,
    compute_semantic_match,
    cosine_similarity,
    cosine_similarity_matrix,
    similarity_to_score,
)
from app.services.text_cleaner import (
    clean_cv_text,
    clean_text,
    clean_whitespace_and_newlines,
    fix_hyphenated_linebreaks,
    normalize_bullet_points,
    normalize_unicode,
    remove_control_characters,
)

__all__ = [
    # AI Provider (cloud | local | auto) — điểm vào chung cho mọi lời gọi AI sinh nội dung
    "AIProviderError",
    "StructuredResult",
    "generate_structured",
    "get_provider_mode",
    "get_provider_status",
    # Ollama Service
    "OllamaServiceError",
    "OllamaConnectionError",
    "OllamaModelNotFoundError",
    "OllamaResponseError",
    "check_ollama_status",
    # Embedding Service
    "EmbeddingServiceError",
    "EmbeddingModelLoadError",
    "get_embedding_model",
    "preload_embedding_model",
    "split_into_chunks",
    "encode_texts",
    "encode_document",
    # CV Extractor
    "CV_EXTRACTION_SYSTEM_INSTRUCTION",
    "build_cv_extraction_prompt",
    "extract_cv_info",
    "extract_cv_info_detailed",
    "normalize_cv_extraction",
    # Gemini Service
    "GeminiServiceError",
    "GeminiConfigError",
    "GeminiAPIError",
    "GeminiQuotaExhaustedError",
    "GeminiResponseError",
    "get_gemini_client",
    # PDF Service
    "PDFServiceError",
    "PDFFileNotFoundError",
    "PDFCorruptedError",
    "PDFEncryptedError",
    "PDFEmptyError",
    "extract_text_from_pdf",
    "extract_pages_text",
    "get_pdf_metadata",
    "extract_text_from_candidate_cv",
    # Hybrid Scoring
    "SkillMatch",
    "HardFilterResult",
    "HybridScoreResult",
    "normalize_skill",
    "match_skills",
    "compute_hard_filter",
    "combine_scores",
    "compute_hybrid_score",
    # Semantic Matching
    "SemanticMatchResult",
    "cosine_similarity",
    "cosine_similarity_matrix",
    "similarity_to_score",
    "build_job_text",
    "compute_semantic_match",
    "compute_job_cv_match",
    # Text Cleaner
    "clean_text",
    "clean_cv_text",
    "remove_control_characters",
    "normalize_unicode",
    "normalize_bullet_points",
    "fix_hyphenated_linebreaks",
    "clean_whitespace_and_newlines",
]
