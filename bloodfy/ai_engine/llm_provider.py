"""
AI Engine — LLM Provider Abstraction.

Supports Gemini (Google) and OpenAI with automatic fallback.
If no API key is configured, all calls return ``None`` — the caller
(e.g. TriageService) falls back to its rule-based engine.

Usage:
    from ai_engine.llm_provider import get_llm_provider

    provider = get_llm_provider()  # returns None if unconfigured
    if provider:
        text = provider.generate(system_prompt, user_prompt)
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger("bloodfy")


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class BaseLLMProvider(ABC):
    """Interface that all LLM providers must implement."""

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
        timeout_seconds: int = 10,
    ) -> Optional[str]:
        """Return raw text from the LLM, or ``None`` on failure."""
        ...


# ---------------------------------------------------------------------------
# Gemini provider
# ---------------------------------------------------------------------------

class GeminiProvider(BaseLLMProvider):
    """Google Gemini (generativeai SDK)."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self._api_key = api_key
        self._model_name = model
        self._model = None

    def _get_model(self):
        if self._model is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self._api_key)
                self._model = genai.GenerativeModel(self._model_name)
            except ImportError:
                logger.error(
                    "google-generativeai package not installed. "
                    "Run: pip install google-generativeai"
                )
                raise
        return self._model

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
        timeout_seconds: int = 10,
    ) -> Optional[str]:
        try:
            model = self._get_model()
            import google.generativeai as genai

            generation_config = genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )

            combined_prompt = f"{system_prompt}\n\n---\n\n{user_prompt}"
            response = model.generate_content(
                combined_prompt,
                generation_config=generation_config,
                request_options={"timeout": timeout_seconds},
            )

            if response and response.text:
                return response.text.strip()
            return None

        except Exception as exc:
            logger.warning("Gemini generation failed: %s", exc)
            return None


# ---------------------------------------------------------------------------
# OpenAI provider
# ---------------------------------------------------------------------------

class OpenAIProvider(BaseLLMProvider):
    """OpenAI (GPT-4o / GPT-4 / GPT-3.5-turbo)."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self._api_key = api_key
        self._model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self._api_key)
            except ImportError:
                logger.error(
                    "openai package not installed. Run: pip install openai"
                )
                raise
        return self._client

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
        timeout_seconds: int = 10,
    ) -> Optional[str]:
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout_seconds,
            )

            if response.choices:
                return response.choices[0].message.content.strip()
            return None

        except Exception as exc:
            logger.warning("OpenAI generation failed: %s", exc)
            return None


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_llm_provider() -> Optional[BaseLLMProvider]:
    """
    Create and return the appropriate LLM provider based on environment
    variables.  Returns ``None`` if no API key is configured — the system
    continues to work using rule-based logic.

    Priority:
        1. ``GEMINI_API_KEY``  → GeminiProvider
        2. ``OPENAI_API_KEY``  → OpenAIProvider
        3. None                → Rule-based fallback
    """
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()

    if gemini_key:
        model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        logger.info("Using Gemini LLM provider (model=%s)", model)
        return GeminiProvider(api_key=gemini_key, model=model)

    if openai_key:
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        logger.info("Using OpenAI LLM provider (model=%s)", model)
        return OpenAIProvider(api_key=openai_key, model=model)

    logger.info("No LLM API key configured — using rule-based engine only")
    return None
