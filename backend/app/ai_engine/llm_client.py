"""
MedAssist AI - Multi-Provider LLM Client
Supports Ollama (free/local), Google Gemini (free tier), and OpenAI.
Auto-detects the best available provider.
"""

import os
import json
import logging
import httpx
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Multi-provider LLM client with automatic fallback chain:
      1. Ollama   (100% free, runs locally, no API key)
      2. Gemini   (free tier: 15 req/min, 1M tokens/day)
      3. OpenAI   (paid, optional)
    """

    def __init__(self):
        from app.config import settings

        self.provider: Optional[str] = None
        self.model: str = ""

        # Provider configuration
        self._openai_key = settings.OPENAI_API_KEY if (
            settings.OPENAI_API_KEY
            and settings.OPENAI_API_KEY not in ("your-api-key-here", "sk-your-openai-api-key-here", "")
        ) else None

        self._gemini_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if self._gemini_key and self._gemini_key in ("your-gemini-api-key-here", ""):
            self._gemini_key = None

        self._ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self._ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")

        self._settings = settings
        self._initialized = False

    async def _detect_provider(self):
        """Auto-detect the best available LLM provider"""
        if self._initialized:
            return

        # 1. Try Ollama first (free, no API key needed)
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{self._ollama_url}/api/tags")
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    model_names = [m.get("name", "") for m in models]

                    # Use configured model, or pick best available
                    if any(self._ollama_model in n for n in model_names):
                        self.provider = "ollama"
                        self.model = self._ollama_model
                    elif model_names:
                        self.provider = "ollama"
                        self.model = model_names[0]

                    if self.provider:
                        logger.info(f"LLM Provider: Ollama ({self.model}) — FREE, local")
                        self._initialized = True
                        return
        except Exception:
            pass

        # 2. Try Gemini (free tier)
        if self._gemini_key:
            self.provider = "gemini"
            self.model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
            logger.info(f"LLM Provider: Google Gemini ({self.model}) — FREE tier")
            self._initialized = True
            return

        # 3. OpenAI (paid)
        if self._openai_key:
            self.provider = "openai"
            self.model = self._settings.LLM_MODEL
            logger.info(f"LLM Provider: OpenAI ({self.model}) — PAID")
            self._initialized = True
            return

        # No LLM available — system will use template fallbacks
        logger.warning(
            "No LLM provider available. Using template fallback responses.\n"
            "  To enable AI:\n"
            "  • Ollama (FREE): brew install ollama && ollama pull llama3.2\n"
            "  • Gemini (FREE): Get key at https://aistudio.google.com/apikey\n"
        )
        self._initialized = True

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> Optional[str]:
        """Send messages to the LLM and return the response text"""
        await self._detect_provider()

        if not self.provider:
            return None

        try:
            if self.provider == "ollama":
                return await self._ollama_chat(messages, temperature, max_tokens)
            elif self.provider == "gemini":
                return await self._gemini_chat(messages, temperature, max_tokens)
            elif self.provider == "openai":
                return await self._openai_chat(messages, temperature, max_tokens)
        except Exception as e:
            logger.error(f"LLM call failed ({self.provider}): {e}")
            return None

    # ─── Ollama (FREE, local) ──────────────────────

    async def _ollama_chat(
        self, messages: List[Dict], temperature: float, max_tokens: int
    ) -> Optional[str]:
        """Call Ollama local server"""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self._ollama_url}/api/chat",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content")

    # ─── Google Gemini (FREE tier) ─────────────────

    async def _gemini_chat(
        self, messages: List[Dict], temperature: float, max_tokens: int
    ) -> Optional[str]:
        """Call Google Gemini API (free tier) with retry for rate limits"""
        import asyncio

        # Convert OpenAI-style messages to Gemini format
        system_instruction = ""
        contents = []

        for msg in messages:
            role = msg["role"]
            text = msg["content"]
            if role == "system":
                system_instruction = text
            elif role == "user":
                contents.append({"role": "user", "parts": [{"text": text}]})
            elif role == "assistant":
                contents.append({"role": "model", "parts": [{"text": text}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self._gemini_key}"
        )

        # Retry with exponential backoff for rate limits
        for attempt in range(3):
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload)

                if resp.status_code == 429 and attempt < 2:
                    wait = 2 ** (attempt + 1)  # 2s, 4s
                    logger.warning(f"Gemini rate limit hit, retrying in {wait}s (attempt {attempt + 1}/3)")
                    await asyncio.sleep(wait)
                    continue

                resp.raise_for_status()
                data = resp.json()

                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text")
        return None

    # ─── OpenAI (paid) ─────────────────────────────

    async def _openai_chat(
        self, messages: List[Dict], temperature: float, max_tokens: int
    ) -> Optional[str]:
        """Call OpenAI API"""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self._openai_key)
        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    @property
    def is_available(self) -> bool:
        return self.provider is not None

    @property
    def provider_info(self) -> str:
        if not self.provider:
            return "None (using template fallbacks)"
        labels = {"ollama": "Ollama (FREE, local)", "gemini": "Google Gemini (FREE tier)", "openai": "OpenAI (paid)"}
        return f"{labels.get(self.provider, self.provider)} — model: {self.model}"


# Global singleton
llm_client = LLMClient()
