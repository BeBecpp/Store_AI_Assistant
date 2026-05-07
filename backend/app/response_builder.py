"""Mongolian template-based answers when no LLM is configured or all providers fail."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.models import ParsedIntent, ProductCard

logger = logging.getLogger(__name__)


def _format_mnt(n: float | int) -> str:
    return f"{int(n):,}"


def _products_to_lines(products: list[ProductCard], max_items: int = 3) -> str:
    lines: list[str] = []
    for p in products[:max_items]:
        lines.append(
            f"• {p.name}\n"
            f"  Үнэ: {_format_mnt(p.price)} ₮ · Үлдэгдэл: {p.stock} ш · Байршил: {p.location}\n"
            f"  Холбоос: {p.url}"
        )
    return "\n\n".join(lines)


def build_fallback_reply(
    user_message: str,
    intent: ParsedIntent,
    products: list[ProductCard],
    in_stock: bool,
) -> str:
    """Generate a helpful MN answer from templates and verified product cards."""
    car = intent.car_model or "таны машин"
    parts: list[str] = []

    # Opening line by dominant intent / symptom
    if intent.symptom == "won_t_start":
        parts.append(
            f"{car} эргэлдэхгүй (асахгүй) байвал ихэвчлэн 12V туслах аккумлятор сул эсвэл "
            "түлхүүр/гал хамгаалагч/цахилгааны холбоосын асуудал байдаг."
        )
        parts.append(
            "Эхлээд эдгээрийг шалгаарай:\n"
            "1) Instrument/Dashboard гэрэл бүдэг үү?\n"
            "2) Smart key түлхүүр ажиллаж байна уу?\n"
            "3) Jump start хийж үзсэн үү (поляр зөв эсэхийг анхаар)?"
        )
    elif intent.category == "engine_oil":
        parts.append(
            f"{car}-д тохох хөдөлгүүрийн тосыг доорх байршил болон үлдэгдлээс сонгоно уу. "
            "Тос солихдоо OEM/зориулалтын ангиллыг баримтлаарай."
        )
    elif intent.intent_type == "stock_check":
        parts.append(
            "Таны асуусан төрлийн барааны үлдэгдэл, байршлыг доорх жагсаалтаас шалгана уу."
        )
    elif intent.intent_type == "location_check":
        parts.append(
            "Барааны тавиурын байршлыг доорх мэдээллээс ашиглана уу. Хэрэв олдохгүй бол "
            "дуудлагаар ажилтанд хандаарай."
        )
    elif intent.intent_type == "price_check":
        parts.append(
            "Үнийг зөвхөн доорх каталогийн мөрөөс авна уу (өрөөсөрөгч үнэ гаргахгүй)."
        )
    else:
        parts.append(
            "Таны асуулгад ойролцоо тохирох сэлбэгийг доор жагсаалаа. "
            "Онош нарийвчилгаа хэрэгтэй бол сервист хандаарай."
        )

    if products:
        parts.append("Тохирох бараа (системээс баталгаажсан):\n" + _products_to_lines(products))
    else:
        parts.append(
            "Одоогоор каталогоос тааруулж чадсангүй. Дэлгүүрийн ажилтан эсвэл оношилгооны "
            "үйлчилгээнд хандаж баталгаажуулна уу."
        )

    parts.append(
        "Чухал: Үнэ, үлдэгдэл, байршил, холбоосыг зөвхөн доорх жагсаалтаас авна — "
        "жагсаалтад байхгүй тоог би зохиохгүй."
    )

    if intent.symptom == "won_t_start" and in_stock:
        parts.append(
            "Jump start хийсэн ч асахгүй бол стартер, hybrid системийн код/оношлуур шаардлагатай "
            "байж болно — аюулгүй газар зогсоогоорой."
        )

    return "\n\n".join(parts)


def symptom_snippets_from_map(symptom: str | None, path: Path) -> list[str]:
    """Load concise troubleshooting hints from symptom_map.json (RAG-ready; MN labels)."""
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except Exception:
        logger.warning("symptom_map.json unreadable at %s", path, exc_info=True)
        return []
    entry = data.get(symptom or "", {})
    causes = entry.get("likely_causes", [])
    safety = entry.get("safety_notes", [])
    out: list[str] = []
    for c in causes[:3]:
        out.append(f"Магадлалтай шалтгаан: {c}")
    for s in safety[:3]:
        out.append(f"Аюулгүй байдал: {s}")
    return out
