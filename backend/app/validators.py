"""Validate assistant output against verified product facts."""

from __future__ import annotations

import re
from typing import Any

from app.models import ProductCard


_PRICE_RE = re.compile(r"([\d,\s]+)\s*₮|₮\s*([\d,\s]+)|(\d[\d,\s]*)\s*(төгрөг|MNT)", re.I)


def _normalize_price_token(t: str) -> int | None:
    digits = re.sub(r"[^\d]", "", t)
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def validate_answer_against_products(reply: str, products: list[ProductCard]) -> str:
    """
    Ensure any mentioned MNT amounts appear in the verified product list.
    If stray invented-looking prices appear, append a safety disclaimer.
    """
    if not products:
        return reply

    allowed = {int(p.price) for p in products}
    found_prices: set[int] = set()
    for m in _PRICE_RE.finditer(reply):
        for g in m.groups():
            if g:
                val = _normalize_price_token(g)
                if val is not None:
                    found_prices.add(val)

    suspicious = [p for p in found_prices if p not in allowed]
    if suspicious:
        note = (
            "\n\nТэмдэглэл: Хариултад тохохгүй үнийн тоо илэрсэн тул зөвхөн доорх барааны жагсаалтын үнийг "
            "баталгаатай гэж үзнэ үү."
        )
        return reply.rstrip() + note
    return reply


def products_for_api(rows: list[dict[str, Any]]) -> list[ProductCard]:
    cards: list[ProductCard] = []
    for p in rows:
        cards.append(
            ProductCard(
                id=str(p["id"]),
                name=str(p["name"]),
                price=p.get("price", 0),
                currency=str(p.get("currency", "MNT")),
                stock=int(p.get("stock", 0)),
                location=str(p.get("location", "")),
                compatible_cars=list(p.get("compatible_cars", [])),
                url=str(p.get("url", "")),
                category=p.get("category"),
            )
        )
    return cards
