from __future__ import annotations

import json
import os
import time
from typing import Any

import httpx

from src.exceptions import ExternalServiceError


class OllamaClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("OLLAMA_URL", "http://ollama:11434")
        self.model = os.getenv("IDEA_PARSER_MODEL", "qwen2.5:7b")
        read_timeout = float(os.getenv("IDEA_PARSER_TIMEOUT_SECONDS", "120"))
        self.timeout = httpx.Timeout(
            connect=10.0,
            read=read_timeout,
            write=10.0,
            pool=10.0,
        )
        self.num_predict = int(os.getenv("IDEA_PARSER_NUM_PREDICT", "120"))
        self.num_ctx = int(os.getenv("IDEA_PARSER_NUM_CTX", "768"))
        self.temperature = float(os.getenv("IDEA_PARSER_TEMPERATURE", "0"))
        self.keep_alive = os.getenv("IDEA_PARSER_KEEP_ALIVE", "30m")
        self._client = httpx.AsyncClient(timeout=self.timeout)

    async def chat_json(self, prompt: str) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": "json",
            "options": {
                "temperature": self.temperature,
                "num_ctx": self.num_ctx,
                "num_predict": self.num_predict,
            },
            "keep_alive": self.keep_alive,
        }

        try:
            started_at = time.perf_counter()
            response = await self._client.post(f"{self.base_url}/api/chat", json=payload)
            if response.is_error:
                raise ExternalServiceError(
                    f"Ollama request failed with status {response.status_code}: {response.text}"
                )
        except httpx.HTTPError as exc:
            raise ExternalServiceError(f"Ollama request failed: {exc}") from exc

        data = response.json()
        data["total_latency_ms"] = int((time.perf_counter() - started_at) * 1000)
        content = data.get("message", {}).get("content", "")
        if not content:
            raise ExternalServiceError("Ollama returned empty content")

        try:
            return content if isinstance(content, dict) else json.loads(content)
        except Exception as exc:
            raise ExternalServiceError(f"Failed to decode Ollama JSON response: {exc}") from exc
