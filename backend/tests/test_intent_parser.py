"""Tests for rule-based intent parsing."""

from app.intent_parser import parse_intent


def test_prius_wont_start_diagnose():
    i = parse_intent("Prius 30 асахгүй байна")
    assert i.car_model == "Prius 30"
    assert i.symptom == "won_t_start"
    assert i.category == "battery"
    assert i.intent_type == "diagnose_and_buy"
    assert i.language == "mn"


def test_battery_stock_check():
    i = parse_intent("аккумлятор байгаа юу")
    assert i.category == "battery"
    assert i.intent_type == "stock_check"


def test_oil_location_prius20():
    i = parse_intent("Prius 20 тос хаана байна")
    assert i.car_model == "Prius 20"
    assert i.category == "engine_oil"
    assert i.intent_type == "location_check"


def test_english_wont_start():
    i = parse_intent("My Prius 30 won't start")
    assert i.car_model == "Prius 30"
    assert i.symptom == "won_t_start"
