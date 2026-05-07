"""Coordinates intent, store search, knowledge snippets, AI, and validation."""

from __future__ import annotations

import logging
from pathlib import Path

from app.ai_client import AIClient
from app.config import Settings, get_settings
from app.intent_parser import parse_intent
from app.models import ChatResponse
from app.response_builder import build_fallback_reply, symptom_snippets_from_map
from app.store_client import BaseStoreClient, build_store_client
from app.validators import products_for_api, validate_answer_against_products

logger = logging.getLogger(__name__)


def _symptom_map_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "symptom_map.json"


class AssistantOrchestrator:
    def __init__(
        self,
        settings: Settings | None = None,
        store: BaseStoreClient | None = None,
        ai: AIClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        # Store integration: swap MockStoreClient → RestStoreClient via STORE_PROVIDER / env.
        self.store = store or build_store_client(
            self.settings.store_provider,
            self.settings.store_api_url,
            self.settings.store_api_key,
            self.settings.store_api_timeout,
        )
        self.ai = ai or AIClient(self.settings)

    def handle_chat(
        self,
        message: str,
        lang: str = "mn",
        session_id: str | None = None,
    ) -> ChatResponse:
        intent = parse_intent(message)
        if lang and lang != "auto":
            intent.language = lang

        try:
            in_stock, out_stock = self.store.search_products(
                query=message,
                car_model=intent.car_model,
                symptom=intent.symptom,
                category=intent.category,
                keywords=intent.keywords,
                limit=5,
            )
        except NotImplementedError:
            logger.error(
                "STORE_PROVIDER=rest but RestStoreClient is not implemented yet — "
                "fill HTTP calls in backend/app/store_client.py (RestStoreClient)."
            )
            return ChatResponse(
                reply=(
                    "Дэлгүүрийн систем одоогоор холбогдоогүй байна (REST adapter тохируулаагүй). "
                    "Түр хүлээгээд дахин оролдоно уу эсвэл ажилтанд хандаарай."
                ),
                intent=intent,
                products=[],
                source="store_unconfigured",
                rag_snippets=None,
            )
        except Exception:
            logger.exception("Product search / store client failed")
            fb = build_fallback_reply(message, intent, [], False)
            return ChatResponse(
                reply=fb,
                intent=intent,
                products=[],
                source="catalog_error",
                rag_snippets=None,
            )

        primary = in_stock[:5]
        if len(primary) < 3:
            primary = (primary + out_stock)[:5]

        product_cards = products_for_api(primary)

        knowledge: list[str] = []
        try:
            knowledge = symptom_snippets_from_map(intent.symptom, _symptom_map_path())
        except Exception:
            logger.warning("Symptom knowledge load failed", exc_info=True)

        reply = self.ai.generate_answer(
            message,
            intent,
            product_cards,
            lang=intent.language,
            knowledge_snippets=knowledge,
        )
        reply = validate_answer_against_products(reply, product_cards)

        return ChatResponse(
            reply=reply,
            intent=intent,
            products=product_cards,
            source="mock_catalog",
            rag_snippets=knowledge or None,
        )
