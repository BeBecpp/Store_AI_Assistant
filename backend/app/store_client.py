"""Store adapters: mock JSON now, REST placeholder for production."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.product_search import ProductSearchEngine


class BaseStoreClient(ABC):
    @abstractmethod
    def search_products(
        self,
        query: str | None = None,
        car_model: str | None = None,
        symptom: str | None = None,
        category: str | None = None,
        keywords: list[str] | None = None,
        limit: int = 5,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Return (in_stock_products, out_of_stock_products)."""

    @abstractmethod
    def get_product_detail(self, product_id: str) -> dict[str, Any] | None:
        ...

    @abstractmethod
    def check_stock(self, product_id: str) -> int | None:
        ...

    @abstractmethod
    def get_product_location(self, product_id: str) -> str | None:
        ...


class MockStoreClient(BaseStoreClient):
    """Loads catalog from local JSON files via ProductSearchEngine."""

    def __init__(self) -> None:
        self._engine = ProductSearchEngine()

    def search_products(
        self,
        query: str | None = None,
        car_model: str | None = None,
        symptom: str | None = None,
        category: str | None = None,
        keywords: list[str] | None = None,
        limit: int = 5,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        return self._engine.search(
            car_model=car_model,
            symptom=symptom,
            category=category,
            query=query,
            extra_keywords=keywords,
            limit=limit,
        )

    def _by_id(self, product_id: str) -> dict[str, Any] | None:
        for p in self._engine._products:
            if p.get("id") == product_id:
                return p
        return None

    def get_product_detail(self, product_id: str) -> dict[str, Any] | None:
        return self._by_id(product_id)

    def check_stock(self, product_id: str) -> int | None:
        p = self._by_id(product_id)
        if not p:
            return None
        return int(p.get("stock", 0))

    def get_product_location(self, product_id: str) -> str | None:
        p = self._by_id(product_id)
        if not p:
            return None
        return str(p.get("location", ""))


class RestStoreClient(BaseStoreClient):
    """
    PRODUCTION INTEGRATION POINT — replace NotImplementedError bodies with real HTTP calls.

    Expected workflow:
      1. Read STORE_API_URL / STORE_API_KEY / STORE_API_TIMEOUT from Settings (already passed in __init__).
      2. Use httpx.Client(base_url=..., headers={"Authorization": "Bearer ..."}, timeout=...) or your auth scheme.
      3. Map JSON responses into the same dict shape as rows in data/products.json so the widget/orchestrator stay unchanged.
      4. search_products must return (in_stock_list, out_of_stock_list) split by stock > 0.

    See also: docs/store-api-integration.md
    """

    def __init__(self, base_url: str, api_key: str, timeout: int = 10) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    def search_products(
        self,
        query: str | None = None,
        car_model: str | None = None,
        symptom: str | None = None,
        category: str | None = None,
        keywords: list[str] | None = None,
        limit: int = 5,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        raise NotImplementedError(
            "Implement HTTP search against STORE_API_URL — see RestStoreClient docstring and docs/store-api-integration.md"
        )

    def get_product_detail(self, product_id: str) -> dict[str, Any] | None:
        raise NotImplementedError(
            "Implement GET product detail — wire Laravel/API route and map JSON to catalog fields."
        )

    def check_stock(self, product_id: str) -> int | None:
        raise NotImplementedError(
            "Implement inventory endpoint or derive stock from product detail response."
        )

    def get_product_location(self, product_id: str) -> str | None:
        raise NotImplementedError(
            "Implement shelf / aisle / branch fields from your store systems."
        )


def build_store_client(provider: str, api_url: str, api_key: str, timeout: int) -> BaseStoreClient:
    """Factory used by AssistantOrchestrator — swap REST implementation without changing routes."""
    if provider.lower() == "rest":
        return RestStoreClient(api_url, api_key, timeout)
    return MockStoreClient()
