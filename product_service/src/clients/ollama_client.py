from __future__ import annotations

import json
import os
from typing import Any

import httpx

from src.exceptions import ExternalServiceError


class OllamaClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("OLLAMA_URL", "http://ollama:11434")
        fallback_urls = os.getenv("OLLAMA_FALLBACK_URLS", "http://host.docker.internal:11434,http://localhost:11434")
        self.base_urls = [self.base_url] + [u.strip() for u in fallback_urls.split(",") if u.strip()]
        self.model = os.getenv("PRODUCT_ANALYSIS_MODEL", "qwen2.5:7b")
        read_timeout = float(os.getenv("PRODUCT_ANALYSIS_TIMEOUT_SECONDS", "120"))
        self.timeout = httpx.Timeout(
            connect=10.0,
            read=read_timeout,
            write=10.0,
            pool=10.0,
        )
        self.temperature = float(os.getenv("PRODUCT_ANALYSIS_TEMPERATURE", "0.2"))
        self.num_ctx = int(os.getenv("PRODUCT_ANALYSIS_NUM_CTX", "2048"))
        self.num_predict = int(os.getenv("PRODUCT_ANALYSIS_NUM_PREDICT", "1200"))
        self.keep_alive = os.getenv("PRODUCT_ANALYSIS_KEEP_ALIVE", "30m")
        self._client = httpx.AsyncClient(timeout=self.timeout)

    async def health(self) -> bool:
        for base_url in self.base_urls:
            try:
                response = await self._client.get(f"{base_url}/api/tags")
                if not response.is_error:
                    return True
            except httpx.HTTPError:
                continue
        return False

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
        response = None
        errors: list[str] = []
        for base_url in self.base_urls:
            try:
                response = await self._client.post(f"{base_url}/api/chat", json=payload)
                if response.is_error:
                    errors.append(f"{base_url} -> HTTP {response.status_code}")
                    continue
                break
            except httpx.HTTPError as exc:
                errors.append(f"{base_url} -> {exc}")
                continue

        if response is None or response.is_error:
            joined_errors = "; ".join(errors) if errors else "unknown error"
            raise ExternalServiceError(f"Ollama request failed across all endpoints: {joined_errors}")

        content = response.json().get("message", {}).get("content")
        if not content:
            raise ExternalServiceError("Ollama returned empty content")

        if isinstance(content, dict):
            return content
        try:
            return json.loads(content)
        except Exception as exc:
            raise ExternalServiceError(f"Failed to decode Ollama JSON response: {exc}") from exc
