"""Product search with scoring; structured for future vector/RAG extension."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _data_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "products.json"


def load_products() -> list[dict[str, Any]]:
    path = _data_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("products", [])


def score_product(
    product: dict[str, Any],
    car_model: str | None,
    symptom: str | None,
    category: str | None,
    query_keywords: list[str],
) -> int:
    score = 0
    compatible = [str(c).lower() for c in product.get("compatible_cars", [])]
    if car_model and car_model.lower() in compatible:
        score += 40
    symptoms = product.get("symptoms", [])
    if symptom and symptom in symptoms:
        score += 30
    if category and product.get("category") == category:
        score += 20
    kw_lower = [k.lower() for k in product.get("keywords", [])]
    for q in query_keywords:
        if q.lower() in kw_lower:
            score += 5
    stock = int(product.get("stock", 0))
    if stock > 0:
        score += 10
    return score


def _deterministic_sort_key(
    product: dict[str, Any],
    car_model: str | None,
    symptom: str | None,
    category: str | None,
    query_keywords: list[str],
) -> tuple[int, str]:
    """
    Higher score first; ties broken by product id (lexicographic) for stable, testable order.
    """
    s = score_product(product, car_model, symptom, category, query_keywords)
    pid = str(product.get("id", ""))
    return (-s, pid)


class ProductSearchEngine:
    """Keyword + compatibility search; swap internals later for vector DB."""

    def __init__(self, products: list[dict[str, Any]] | None = None):
        self._products = products if products is not None else load_products()

    def search(
        self,
        car_model: str | None = None,
        symptom: str | None = None,
        category: str | None = None,
        query: str | None = None,
        extra_keywords: list[str] | None = None,
        limit: int = 5,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Returns (in_stock_ranked, out_of_stock_ranked).
        Top 3-5 in-stock primary; OOS listed separately for UI.
        Sorting is deterministic: higher score first, ties broken by product `id` (lexicographic).
        """
        qk = list(extra_keywords or [])
        if query:
            qk.extend(query.replace(",", " ").split())

        in_stock = [p for p in self._products if int(p.get("stock", 0)) > 0]
        out_stock = [p for p in self._products if int(p.get("stock", 0)) <= 0]

        sort_key = lambda p: _deterministic_sort_key(p, car_model, symptom, category, qk)
        in_stock.sort(key=sort_key)
        out_stock.sort(key=sort_key)

        top_in = in_stock[:limit]
        top_oos = out_stock[: max(0, limit - len(top_in))]
        return top_in, top_oos
