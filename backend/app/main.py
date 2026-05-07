"""FastAPI application — API entrypoint, CORS, routes."""

from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.models import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    IntentDebugRequest,
    ParsedIntent,
)
from app.orchestrator import AssistantOrchestrator
from app.intent_parser import parse_intent
from app.product_search import ProductSearchEngine

logger = logging.getLogger(__name__)


def get_orchestrator(settings: Settings = Depends(get_settings)) -> AssistantOrchestrator:
    return AssistantOrchestrator(settings=settings)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, debug=settings.debug)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from pathlib import Path

    frontend_dir = (
        Path(settings.frontend_static_path)
        if settings.frontend_static_path
        else Path(__file__).resolve().parent.parent.parent / "frontend"
    )
    if frontend_dir.exists():
        app.mount("/widget", StaticFiles(directory=str(frontend_dir)), name="widget")

    # TODO(rate-limit): add Redis/slowapi per IP + session (see docs/architecture.md)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Do not leak raw pydantic traces to clients unless DEBUG is enabled."""
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Invalid request body or parameters.",
                "errors": exc.errors() if settings.debug else None,
            },
        )

    @app.get("/", response_class=HTMLResponse)
    def root():
        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/><title>{settings.app_name}</title></head>
<body style="font-family:system-ui;padding:2rem">
<h1>{settings.app_name}</h1>
<p>Health: <a href="/health">/health</a></p>
<p>API docs: <a href="/docs">/docs</a></p>
<p>Widget demo: <a href="/widget/index.html">/widget/index.html</a></p>
</body></html>"""

    @app.get("/health", response_model=HealthResponse)
    def health():
        return HealthResponse(
            status="ok",
            app=settings.app_name,
            store_provider=settings.store_provider,
        )

    @app.post("/api/chat", response_model=ChatResponse)
    def chat(
        body: ChatRequest,
        orch: AssistantOrchestrator = Depends(get_orchestrator),
    ):
        msg = body.message.strip()
        if len(msg) > settings.max_message_length:
            raise HTTPException(400, "Message too long")
        try:
            return orch.handle_chat(msg, lang=body.lang or "mn", session_id=body.session_id)
        except HTTPException:
            raise
        except Exception:
            logger.exception("Chat orchestration failed")
            raise HTTPException(500, "Internal server error") from None

    @app.post("/api/intent", response_model=ParsedIntent)
    def intent_debug(body: IntentDebugRequest):
        if len(body.message.strip()) > get_settings().max_message_length:
            raise HTTPException(400, "Message too long")
        try:
            return parse_intent(body.message)
        except Exception:
            logger.exception("Intent parse failed")
            raise HTTPException(500, "Could not parse intent")

    @app.get("/api/products/search")
    def products_search(
        q: str | None = Query(None),
        car_model: str | None = Query(None),
        symptom: str | None = Query(None),
        category: str | None = Query(None),
    ):
        try:
            engine = ProductSearchEngine()
            ins, oos = engine.search(
                car_model=car_model,
                symptom=symptom,
                category=category,
                query=q,
                limit=5,
            )
        except Exception:
            logger.exception("Product search endpoint failed")
            raise HTTPException(503, "Catalog temporarily unavailable")
        return {
            "in_stock": ins,
            "out_of_stock": oos,
        }

    return app


app = create_app()
