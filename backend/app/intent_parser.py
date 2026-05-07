"""Rule-based intent parsing for Mongolian and English."""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.models import ParsedIntent


def _data_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "data"


def _load_json(name: str) -> dict:
    path = _data_dir() / name
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


# Symptom keywords -> canonical symptom id
SYMPTOM_KEYWORDS: dict[str, str] = {
    # won't start
    "асахгүй": "won_t_start",
    "асахгүй байна": "won_t_start",
    "can't start": "won_t_start",
    "cannot start": "won_t_start",
    "won't start": "won_t_start",
    "wont start": "won_t_start",
    "no crank": "won_t_start",
    "dead battery": "won_t_start",
    # dashboard dim
    "бүдэг": "dashboard_dim",
    "dim": "dashboard_dim",
    "dashboard": "dashboard_dim",
    # smart key
    "smart key": "smart_key_not_working",
    "түлхүүр": "smart_key_not_working",
    # brakes
    "тормос": "brake_noise",
    "brake": "brake_noise",
    "squeal": "brake_noise",
    # lights
    "гэрэл": "headlight_dim",
    "headlight": "headlight_dim",
    # wipers
    "аяга": "wiper_streak",
    "wiper": "wiper_streak",
    # overheating
    "халах": "overheating",
    "overheat": "overheating",
}

# Category hints -> category id
CATEGORY_KEYWORDS: dict[str, str] = {
    "аккумлятор": "battery",
    "battery": "battery",
    "аккум": "battery",
    "12v": "battery",
    "jump": "jump_starter",
    "жампер": "jump_starter",
    "starter pack": "jump_starter",
    "terminal": "battery_terminal",
    "хавчаа": "battery_terminal",
    "fuse": "fuse",
    "гал хамгаалагч": "fuse",
    "тос": "engine_oil",
    "oil": "engine_oil",
    "engine oil": "engine_oil",
    "тормос": "brake_pad",
    "brake pad": "brake_pad",
    "шторк": "brake_pad",
    "bulb": "headlight_bulb",
    "ламп": "headlight_bulb",
    "wiper": "wiper_blade",
    "аяга": "wiper_blade",
    "tire": "tire_inflator",
    "дугуй": "tire_inflator",
    "inflator": "tire_inflator",
    "obd": "obd2_scanner",
    "оношлуур": "obd2_scanner",
    "scanner": "obd2_scanner",
    "coolant": "coolant",
    "сүүлээр": "coolant",
    "антифриз": "coolant",
    "air filter": "air_filter",
    "агаарын шүүлтүүр": "air_filter",
    "cabin": "cabin_filter",
    "салоны шүүлтүүр": "cabin_filter",
    "spark": "spark_plug",
    "гал түүдэг": "spark_plug",
    "holder": "accessory",
    "утасны тулгуур": "accessory",
    "phone holder": "accessory",
}

# Intent type patterns
STOCK_PATTERNS = re.compile(
    r"(байгаа\s*юу|үлдэгдэл|stock|available|in stock)",
    re.I,
)
LOCATION_PATTERNS = re.compile(
    r"(хаана|байршил|where|location|хэдэн\s*давхар)",
    re.I,
)
PRICE_PATTERNS = re.compile(
    r"(үнэ|price|хэд\s*төгрөг|cost)",
    re.I,
)


def _extract_car_model(text: str, aliases: dict[str, list[str]]) -> str | None:
    lower = text.lower()
    # Known models from alias keys and values
    for canonical, names in aliases.items():
        pool = [canonical] + names
        for name in pool:
            if name.lower() in lower:
                return canonical
    # Regex for Prius / Camry style
    m = re.search(
        r"\b(Prius\s*\d+|Toyota\s+[A-Za-z0-9\s]+|Camry|Corolla|RAV4|Land Cruiser)\b",
        text,
        re.I,
    )
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()
    return None


def _extract_symptom(text: str) -> str | None:
    lower = text.lower()
    # Longer phrases first
    sorted_kw = sorted(SYMPTOM_KEYWORDS.keys(), key=len, reverse=True)
    for kw in sorted_kw:
        if kw.lower() in lower:
            return SYMPTOM_KEYWORDS[kw]
    return None


def _extract_category(text: str) -> str | None:
    lower = text.lower()
    sorted_kw = sorted(CATEGORY_KEYWORDS.keys(), key=len, reverse=True)
    for kw in sorted_kw:
        if kw.lower() in lower:
            return CATEGORY_KEYWORDS[kw]
    return None


def _extract_keywords(text: str) -> list[str]:
    tokens = re.findall(r"[\w\u0400-\u04FF]+", text.lower())
    stop = {"байна", "юу", "энд", "надад", "my", "the", "a", "is", "and", "or"}
    return [t for t in tokens if len(t) > 1 and t not in stop][:20]


def _infer_intent_type(
    text: str,
    has_car: bool,
    symptom: str | None,
    category: str | None,
) -> str:
    if STOCK_PATTERNS.search(text):
        return "stock_check"
    if LOCATION_PATTERNS.search(text):
        return "location_check"
    if PRICE_PATTERNS.search(text):
        return "price_check"
    if category and not has_car and not symptom:
        return "product_search"
    if has_car or symptom:
        return "diagnose_and_buy"
    if category:
        return "product_search"
    return "general_help"


def parse_intent(message: str) -> ParsedIntent:
    """Parse user message into structured intent."""
    text = message.strip()
    aliases = _load_json("car_aliases.json")
    car_model = _extract_car_model(text, aliases)
    symptom = _extract_symptom(text)
    category = _extract_category(text)

    # If symptom implies battery category for won't start
    if symptom == "won_t_start" and category is None:
        category = "battery"

    keywords = _extract_keywords(text)
    language = "mn" if re.search(r"[\u0400-\u04FF]", text) else "en"

    intent_type = _infer_intent_type(text, bool(car_model), symptom, category)

    return ParsedIntent(
        car_model=car_model,
        symptom=symptom,
        category=category,
        intent_type=intent_type,
        language=language,
        keywords=keywords,
    )
