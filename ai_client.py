"""Klien chat AI yang kompatibel dengan OpenAI API.

Bisa dipakai untuk OpenAI, 9Router, Ollama, dan layanan lain yang menyediakan
endpoint /chat/completions yang sama.
"""
from __future__ import annotations

import httpx


class AIError(Exception):
    """Error saat memanggil API AI."""


class AIClient:
    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    async def chat(self, messages: list, temperature: float = 0.7,
                   max_tokens: int = 500) -> str:
        """Kirim daftar pesan (termasuk system prompt) dan kembalikan jawaban."""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.base_url}/chat/completions",
                                         json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise AIError(f"Tidak bisa menghubungi {self.base_url}: {exc}") from exc
        if resp.status_code != 200:
            raise AIError(f"API mengembalikan {resp.status_code}: {resp.text[:300]}")
        try:
            content = resp.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as exc:
            raise AIError(f"Respons API tidak bisa dibaca: {resp.text[:300]}") from exc
        return (content or "").strip()
