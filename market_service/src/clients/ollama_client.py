from __future__ import annotations

import json
import os
from typing import Any

import httpx

from src.exceptions import ExternalServiceError


class OllamaClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("OLLAMA_URL", "http://ollama:11434")
        self.model = os.getenv("IDEA_PARSER_MODEL", "qwen2.5:7b")
        self.timeout = httpx.Timeout(float(os.getenv("IDEA_PARSER_TIMEOUT_SECONDS", "30")))
        self.num_predict = int(os.getenv("IDEA_PARSER_NUM_PREDICT", "220"))

    async def chat_json(self, prompt: str) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0,
                "num_ctx": 1024,
                "num_predict": self.num_predict,
            },
            "keep_alive": "10m",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ExternalServiceError(f"Ollama request failed: {exc}") from exc

        data = response.json()
        content = data.get("message", {}).get("content", "")
        if not content:
            raise ExternalServiceError("Ollama returned empty content")

        try:
            return content if isinstance(content, dict) else json.loads(content)
        except Exception as exc:
            raise ExternalServiceError(f"Failed to decode Ollama JSON response: {exc}") from exc
