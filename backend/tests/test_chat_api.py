"""Integration tests for chat API and fallback answers."""

import os

from fastapi.testclient import TestClient

os.environ.setdefault("OLLAMA_BASE_URL", "")
os.environ.setdefault("OPENAI_API_KEY", "")
os.environ.setdefault("GEMINI_API_KEY", "")

from app.main import app  # noqa: E402
from app.response_builder import build_fallback_reply  # noqa: E402
from app.models import ParsedIntent, ProductCard  # noqa: E402
from app.validators import products_for_api  # noqa: E402
from app.product_search import load_products  # noqa: E402


client = TestClient(app)


def test_chat_prius_wont_start_replies_and_products():
    r = client.post(
        "/api/chat",
        json={"message": "Prius 30 асахгүй байна. Аккумлятор хэрэгтэй юу?", "lang": "mn"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "reply" in data and data["reply"]
    assert data["intent"]["car_model"] == "Prius 30"
    assert data["products"]
    names = [p["name"] for p in data["products"]]
    assert any("Battery" in n or "Аккум" in n or "12V" in n for n in names)


def test_battery_stock_check_returns_battery_products():
    r = client.post("/api/chat", json={"message": "аккумлятор байгаа юу"})
    assert r.status_code == 200
    data = r.json()
    assert data["intent"]["intent_type"] == "stock_check"
    assert data["products"]
    assert any(p["category"] == "battery" for p in data["products"])


def test_oil_location_returns_engine_oil():
    r = client.post("/api/chat", json={"message": "Prius 20 тос хаана байна"})
    assert r.status_code == 200
    data = r.json()
    assert data["intent"]["category"] == "engine_oil"
    cats = {p.get("category") for p in data["products"]}
    assert "engine_oil" in cats


def test_response_includes_grounding_disclaimer():
    """Fallback and validator stress that prices must come from catalog data."""
    r = client.post(
        "/api/chat",
        json={"message": "Mars rover turbo encabulator part number XYZ999"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "зохиохгүй" in data["reply"] or "баталгаажсан" in data["reply"]


def test_fallback_builder_formats_prices():
    rows = [p for p in load_products() if p["id"] == "bat-prius30-001"]
    cards = products_for_api(rows)
    intent = ParsedIntent(
        car_model="Prius 30",
        symptom="won_t_start",
        category="battery",
        intent_type="diagnose_and_buy",
        language="mn",
    )
    reply = build_fallback_reply("test", intent, cards, True)
    assert "380,000" in reply or "380000" in reply.replace(",", "")
