"""Tests for product scoring and ranking."""

from app.product_search import ProductSearchEngine, load_products


def test_prius_wont_start_prefers_battery():
    engine = ProductSearchEngine()
    ins, _ = engine.search(car_model="Prius 30", symptom="won_t_start", category="battery", limit=5)
    assert ins
    assert ins[0]["category"] == "battery"
    assert int(ins[0]["stock"]) > 0


def test_out_of_stock_not_primary_when_alternatives_exist():
    engine = ProductSearchEngine()
    ins, oos = engine.search(car_model="Prius 30", symptom="won_t_start", category="battery", limit=5)
    ids_in = {p["id"] for p in ins}
    assert "bat-prius30-001" in ids_in
    # OOS product should not appear before in-stock in primary in_stock list
    if "bat-prius30-oem-002" in ids_in:
        assert ins[0]["stock"] > 0


def test_search_is_deterministic_for_same_inputs():
    engine = ProductSearchEngine()
    a1, b1 = engine.search(car_model="Prius 30", symptom="won_t_start", category="battery", limit=5)
    a2, b2 = engine.search(car_model="Prius 30", symptom="won_t_start", category="battery", limit=5)
    assert [p["id"] for p in a1] == [p["id"] for p in a2]
    assert [p["id"] for p in b1] == [p["id"] for p in b2]


def test_load_products_count():
    products = load_products()
    assert len(products) >= 15

