"""
tests/test_embedding_service.py — Unit test cho module embedding_service (sentence-transformers)

Phần lớn test dùng mô hình giả lập để chạy nhanh; nhóm TestRealModel dùng mô hình thật
và tự bỏ qua nếu chưa tải mô hình (chạy download_embedding_model.py trước).
"""

import unittest
from unittest import mock

import numpy as np

from app.services import embedding_service
from app.services.embedding_service import (
    EmbeddingModelLoadError,
    encode_document,
    encode_texts,
    split_into_chunks,
)


class FakeModel:
    """Mô hình giả: vector 4 chiều phụ thuộc độ dài văn bản."""

    max_seq_length = 128

    def __init__(self):
        self.calls = []

    def get_embedding_dimension(self):
        return 4

    def encode(self, texts, batch_size=32, normalize_embeddings=False, **kwargs):
        self.calls.append(list(texts))
        vectors = np.array([[len(t), 1.0, 2.0, 3.0] for t in texts], dtype=np.float64)
        if normalize_embeddings:
            vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors


class TestSplitIntoChunks(unittest.TestCase):
    """Kiểm thử chia văn bản dài thành đoạn."""

    def test_short_text_single_chunk(self):
        self.assertEqual(split_into_chunks("Python  FastAPI\nMySQL"), ["Python FastAPI MySQL"])

    def test_empty_text(self):
        self.assertEqual(split_into_chunks("   "), [])
        self.assertEqual(split_into_chunks(None), [])

    def test_long_text_chunks_with_overlap(self):
        words = [f"w{i}" for i in range(25)]
        chunks = split_into_chunks(" ".join(words), max_words=10, overlap=2)
        self.assertEqual(chunks[0].split(), words[0:10])
        self.assertEqual(chunks[1].split(), words[8:18])
        self.assertEqual(chunks[-1].split()[-1], "w24")
        self.assertTrue(all(len(c.split()) <= 10 for c in chunks))

    def test_invalid_overlap(self):
        with self.assertRaises(ValueError):
            split_into_chunks("a b c", max_words=5, overlap=5)


class TestEncoding(unittest.TestCase):
    """Kiểm thử mã hóa vector với mô hình giả lập."""

    def setUp(self):
        self.fake = FakeModel()
        patcher = mock.patch.object(embedding_service, "get_embedding_model", return_value=self.fake)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_encode_texts_shape_and_dtype(self):
        vectors = encode_texts(["Python", "Java developer"])
        self.assertEqual(vectors.shape, (2, 4))
        self.assertEqual(vectors.dtype, np.float32)
        np.testing.assert_allclose(np.linalg.norm(vectors, axis=1), [1.0, 1.0], rtol=1e-5)

    def test_encode_texts_empty_raises(self):
        with self.assertRaises(ValueError):
            encode_texts([])

    def test_encode_document_chunks_long_text_and_normalizes(self):
        text = " ".join(["word"] * 200)
        vector = encode_document(text)
        self.assertEqual(vector.shape, (4,))
        self.assertAlmostEqual(float(np.linalg.norm(vector)), 1.0, places=5)
        self.assertGreater(len(self.fake.calls[0]), 1)  # đã chia thành nhiều đoạn

    def test_encode_document_empty_raises(self):
        with self.assertRaises(ValueError):
            encode_document("  ")


class TestModelLoading(unittest.TestCase):
    """Kiểm thử nạp mô hình (không tải thật)."""

    def setUp(self):
        embedding_service.reset_embedding_model()
        self.addCleanup(embedding_service.reset_embedding_model)

    def test_model_loaded_once_and_cached(self):
        with mock.patch("sentence_transformers.SentenceTransformer", return_value=FakeModel()) as ctor:
            first = embedding_service.get_embedding_model()
            second = embedding_service.get_embedding_model()
        self.assertIs(first, second)
        ctor.assert_called_once()
        self.assertEqual(ctor.call_args.kwargs["device"], embedding_service.EMBEDDING_DEVICE)
        self.assertTrue(embedding_service.is_model_loaded())

    def test_load_failure_raises_custom_error(self):
        with mock.patch("sentence_transformers.SentenceTransformer", side_effect=OSError("offline")):
            with self.assertRaises(EmbeddingModelLoadError):
                embedding_service.get_embedding_model()
        self.assertFalse(embedding_service.is_model_loaded())

    def test_preload_does_not_raise(self):
        with mock.patch("sentence_transformers.SentenceTransformer", side_effect=OSError("offline")):
            self.assertFalse(embedding_service.preload_embedding_model())


def _model_is_cached() -> bool:
    cache = embedding_service.get_cache_dir()
    return cache.exists() and any(cache.glob("*paraphrase-multilingual-MiniLM-L12-v2*"))


@unittest.skipUnless(_model_is_cached(), "Chưa tải mô hình nhúng (chạy download_embedding_model.py)")
class TestRealModel(unittest.TestCase):
    """Kiểm thử với mô hình thật paraphrase-multilingual-MiniLM-L12-v2."""

    def test_dimension_is_384(self):
        self.assertEqual(embedding_service.get_embedding_dimension(), 384)

    def test_multilingual_semantic_similarity(self):
        vectors = encode_texts([
            "Lập trình viên backend sử dụng Python và FastAPI",
            "Backend developer experienced with Python and FastAPI",
            "Nhân viên kế toán tổng hợp, lập báo cáo thuế",
        ])
        same_meaning = float(vectors[0] @ vectors[1])
        unrelated = float(vectors[0] @ vectors[2])
        self.assertGreater(same_meaning, 0.7)
        self.assertGreater(same_meaning, unrelated + 0.3)


if __name__ == "__main__":
    unittest.main()
