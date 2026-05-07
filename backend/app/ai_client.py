"""Pluggable AI providers with deterministic fallback.

Secrets (OPENAI_API_KEY, GEMINI_API_KEY) live only in backend settings — never ship to the browser.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.config import Settings
from app.models import ParsedIntent, ProductCard
from app.response_builder import build_fallback_reply

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """You are a helpful AI assistant for an auto parts store.

Rules:
- Answer in Mongolian unless user clearly asks another language.
- Use only the verified product data provided in CONTEXT.
- Never invent price, stock, store location, product URL, or compatibility.
- If uncertain, say what to check next.
- Give practical step-by-step guidance.
- Recommend maximum 3 products.
- Mention safety warnings when relevant.

USER MESSAGE:
{user_message}

PARSED INTENT:
{intent_json}

VERIFIED PRODUCTS:
{products_json}

KNOWLEDGE SNIPPETS:
{knowledge_json}

Return a helpful answer."""


class AIClient:
    def __init__(self, settings: Settings):
        self._settings = settings

    def generate_answer(
        self,
        user_message: str,
        intent: ParsedIntent,
        products: list[ProductCard],
        lang: str = "mn",
        knowledge_snippets: list[str] | None = None,
    ) -> str:
        intent_dict = intent.model_dump()
        products_payload = [p.model_dump() for p in products[:5]]
        knowledge = knowledge_snippets or []

        # Provider order: Ollama → OpenAI → Gemini → deterministic Mongolian fallback.
        # Empty strings must NOT activate a provider (common .env mistake).
        if self._ollama_configured():
            out = self._try_ollama(
                user_message, intent_dict, products_payload, knowledge, lang
            )
            if out:
                return out
            logger.info("Ollama unreachable or returned empty; trying next provider or fallback.")

        if self._openai_configured():
            out = self._try_openai(
                user_message, intent_dict, products_payload, knowledge, lang
            )
            if out:
                return out
            logger.info("OpenAI call failed or empty; trying next provider or fallback.")

        if self._gemini_configured():
            out = self._try_gemini(
                user_message, intent_dict, products_payload, knowledge, lang
            )
            if out:
                return out
            logger.info("Gemini call failed or empty; using rule-based fallback.")

        in_stock = any(p.stock > 0 for p in products)
        return build_fallback_reply(user_message, intent, products, in_stock)

    def _ollama_configured(self) -> bool:
        base = (self._settings.ollama_base_url or "").strip()
        model = (self._settings.ollama_model or "").strip()
        return bool(base and model)

    def _openai_configured(self) -> bool:
        return bool((self._settings.openai_api_key or "").strip())

    def _gemini_configured(self) -> bool:
        return bool((self._settings.gemini_api_key or "").strip())

    def _build_prompt(
        self,
        user_message: str,
        intent_dict: dict[str, Any],
        products_payload: list[dict[str, Any]],
        knowledge: list[str],
    ) -> str:
        return PROMPT_TEMPLATE.format(
            user_message=user_message,
            intent_json=json.dumps(intent_dict, ensure_ascii=False),
            products_json=json.dumps(products_payload, ensure_ascii=False),
            knowledge_json=json.dumps(knowledge, ensure_ascii=False),
        )

    def _try_ollama(
        self,
        user_message: str,
        intent_dict: dict[str, Any],
        products_payload: list[dict[str, Any]],
        knowledge: list[str],
        lang: str,
    ) -> str | None:
        base = self._settings.ollama_base_url.strip().rstrip("/")
        url = f"{base}/api/generate"
        prompt = self._build_prompt(user_message, intent_dict, products_payload, knowledge)
        body = {
            "model": self._settings.ollama_model.strip(),
            "prompt": prompt,
            "stream": False,
        }
        try:
            with httpx.Client(timeout=60.0) as client:
                r = client.post(url, json=body)
                r.raise_for_status()
                data = r.json()
                return (data.get("response") or "").strip() or None
        except Exception:
            logger.exception("Ollama request failed")
            return None

    def _try_openai(
        self,
        user_message: str,
        intent_dict: dict[str, Any],
        products_payload: list[dict[str, Any]],
        knowledge: list[str],
        lang: str,
    ) -> str | None:
        prompt = self._build_prompt(user_message, intent_dict, products_payload, knowledge)
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._settings.openai_api_key.strip()}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self._settings.openai_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
        }
        try:
            with httpx.Client(timeout=60.0) as client:
                r = client.post(url, headers=headers, json=body)
                r.raise_for_status()
                data = r.json()
                return data["choices"][0]["message"]["content"].strip()
        except Exception:
            logger.exception("OpenAI request failed")
            return None

    def _try_gemini(
        self,
        user_message: str,
        intent_dict: dict[str, Any],
        products_payload: list[dict[str, Any]],
        knowledge: list[str],
        lang: str,
    ) -> str | None:
        prompt = self._build_prompt(user_message, intent_dict, products_payload, knowledge)
        key = self._settings.gemini_api_key.strip()
        model = self._settings.gemini_model
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        )
        try:
            with httpx.Client(timeout=60.0) as client:
                r = client.post(
                    url,
                    params={"key": key},
                    json={"contents": [{"parts": [{"text": prompt}]}]},
                )
                r.raise_for_status()
                data = r.json()
                parts = data["candidates"][0]["content"]["parts"]
                text = "".join(p.get("text", "") for p in parts)
                return text.strip() or None
        except Exception:
            logger.exception("Gemini request failed")
            return None
