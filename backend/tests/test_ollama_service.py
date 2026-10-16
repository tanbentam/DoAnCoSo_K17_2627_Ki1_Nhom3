"""
tests/test_ollama_service.py — Unit test cho service adapter Ollama (mô hình cục bộ)

HTTP tới Ollama được giả lập (mock httpx), không cần Ollama đang chạy.
"""

import json
import unittest
from typing import List
from unittest import mock

import httpx
from pydantic import BaseModel

from app.services import ollama_service
from app.services.ollama_service import (
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaResponseError,
    OllamaServiceError,
    build_chat_payload,
    check_ollama_status,
    generate_structured_detailed,
)


class SampleSchema(BaseModel):
    full_name: str
    skills: List[str]


def _chat_response(content: str, status_code: int = 200):
    return httpx.Response(
        status_code,
        json={"message": {"role": "assistant", "content": content}, "eval_count": 40, "eval_duration": 2_000_000_000,
              "prompt_eval_count": 500, "load_duration": 0},
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )


class TestBuildPayload(unittest.TestCase):

    def test_payload_constrains_output_with_schema(self):
        payload = build_chat_payload("CV", SampleSchema, "Bạn là HR", "qwen2.5:7b")
        self.assertEqual(payload["model"], "qwen2.5:7b")
        self.assertEqual(payload["format"], SampleSchema.model_json_schema())
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["options"]["num_ctx"], ollama_service.OLLAMA_NUM_CTX)
        self.assertEqual(payload["keep_alive"], ollama_service.OLLAMA_KEEP_ALIVE)

    def test_system_prompt_includes_instruction_and_schema(self):
        payload = build_chat_payload("CV", SampleSchema, "Bạn là HR", "m")
        system, user = payload["messages"]
        self.assertEqual((system["role"], user["role"], user["content"]), ("system", "user", "CV"))
        self.assertTrue(system["content"].startswith("Bạn là HR"))
        self.assertIn(json.dumps(SampleSchema.model_json_schema(), ensure_ascii=False), system["content"])


class TestGenerateStructured(unittest.TestCase):

    def test_returns_validated_data_and_meta(self):
        with mock.patch.object(ollama_service.httpx, "post",
                               return_value=_chat_response('{"full_name": "Nguyễn Văn A", "skills": ["Python"]}')):
            result = generate_structured_detailed("CV", SampleSchema)
        self.assertEqual(result.data, SampleSchema(full_name="Nguyễn Văn A", skills=["Python"]))
        self.assertEqual((result.provider, result.model), ("ollama", ollama_service.OLLAMA_MODEL))

    def test_invalid_json_retried_then_succeeds(self):
        responses = [_chat_response('{"full_name": 1}'), _chat_response('{"full_name": "A", "skills": []}')]
        with mock.patch.object(ollama_service.httpx, "post", side_effect=responses) as post:
            result = generate_structured_detailed("CV", SampleSchema, max_retries=1)
        self.assertEqual(post.call_count, 2)
        self.assertEqual(result.attempts[0], f"{ollama_service.OLLAMA_MODEL}: JSON sai schema")

    def test_invalid_json_after_retries_raises(self):
        with mock.patch.object(ollama_service.httpx, "post", return_value=_chat_response("")):
            with self.assertRaises(OllamaResponseError):
                generate_structured_detailed("CV", SampleSchema, max_retries=1)

    def test_connection_error(self):
        with mock.patch.object(ollama_service.httpx, "post", side_effect=httpx.ConnectError("refused")):
            with self.assertRaises(OllamaConnectionError) as ctx:
                generate_structured_detailed("CV", SampleSchema)
        self.assertIn("ollama serve", str(ctx.exception))

    def test_model_not_found(self):
        with mock.patch.object(ollama_service.httpx, "post",
                               return_value=_chat_response('{"error": "model not found"}', 404)):
            with self.assertRaises(OllamaModelNotFoundError) as ctx:
                generate_structured_detailed("CV", SampleSchema, model="llama-x")
        self.assertIn("ollama pull llama-x", str(ctx.exception))

    def test_timeout(self):
        with mock.patch.object(ollama_service.httpx, "post", side_effect=httpx.ReadTimeout("slow")):
            with self.assertRaises(OllamaServiceError):
                generate_structured_detailed("CV", SampleSchema)

    def test_empty_prompt(self):
        with self.assertRaises(ValueError):
            generate_structured_detailed(" ", SampleSchema)


class TestStatus(unittest.TestCase):

    def test_model_ready(self):
        resp = httpx.Response(200, json={"models": [{"name": ollama_service.OLLAMA_MODEL}]},
                              request=httpx.Request("GET", "http://x/api/tags"))
        with mock.patch.object(ollama_service.httpx, "get", return_value=resp):
            status = check_ollama_status()
        self.assertTrue(status["reachable"])
        self.assertTrue(status["model_ready"])

    def test_model_missing(self):
        resp = httpx.Response(200, json={"models": [{"name": "other:1b"}]}, request=httpx.Request("GET", "http://x"))
        with mock.patch.object(ollama_service.httpx, "get", return_value=resp):
            self.assertFalse(check_ollama_status()["model_ready"])

    def test_unreachable(self):
        with mock.patch.object(ollama_service.httpx, "get", side_effect=httpx.ConnectError("refused")):
            status = check_ollama_status()
        self.assertFalse(status["reachable"])
        self.assertIn("ConnectError", status["error"])


if __name__ == "__main__":
    unittest.main()
