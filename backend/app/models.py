"""Pydantic models for API requests and responses."""

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    lang: str = Field(default="mn", max_length=10)
    session_id: str | None = Field(default=None, max_length=128)


class ParsedIntent(BaseModel):
    car_model: str | None = None
    symptom: str | None = None
    category: str | None = None
    intent_type: str = "general_help"
    language: str = "mn"
    keywords: list[str] = Field(default_factory=list)


class ProductCard(BaseModel):
    id: str
    name: str
    price: float | int
    currency: str = "MNT"
    stock: int
    location: str
    compatible_cars: list[str] = Field(default_factory=list)
    url: str
    category: str | None = None


class ChatResponse(BaseModel):
    reply: str
    intent: ParsedIntent
    products: list[ProductCard]
    source: str = "mock_catalog"
    rag_snippets: list[str] | None = None


class IntentDebugRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)


class ProductSearchQuery(BaseModel):
    q: str | None = None
    car_model: str | None = None
    symptom: str | None = None
    category: str | None = None


class HealthResponse(BaseModel):
    status: str
    app: str
    store_provider: str


class ErrorResponse(BaseModel):
    detail: str


class RootInfo(BaseModel):
    service: str
    docs: str
    health: str
    chat: str
