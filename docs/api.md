# HTTP API

Base URL examples use `http://127.0.0.1:8000`. All JSON bodies use UTF-8.

---

## `GET /`

Simple HTML landing page with links to `/health`, `/docs`, and `/widget/index.html`.

---

## `GET /health`

**Response**

```json
{
  "status": "ok",
  "app": "AI Store Assistant",
  "store_provider": "mock"
}
```

---

## `POST /api/chat`

Main assistant endpoint.

**Request**

```json
{
  "message": "Prius 30 асахгүй байна. Аккумлятор хэрэгтэй юу?",
  "lang": "mn",
  "session_id": "optional-session-id"
}
```

| Field | Notes |
| ----- | ----- |
| `message` | Required. Max length 1000 characters (configurable via `MAX_MESSAGE_LENGTH`). |
| `lang` | Optional; defaults to `mn`. Also inferred from script if absent. |
| `session_id` | Optional future hook for sessions / rate limits. |

**Response**

```json
{
  "reply": "Prius 30 асахгүй байгаа бол ...",
  "intent": {
    "car_model": "Prius 30",
    "symptom": "won_t_start",
    "category": "battery",
    "intent_type": "diagnose_and_buy",
    "language": "mn",
    "keywords": ["prius", "30", "..."]
  },
  "products": [
    {
      "id": "bat-prius30-001",
      "name": "Prius 30 12V Battery",
      "price": 380000,
      "currency": "MNT",
      "stock": 4,
      "location": "2-р давхар, Аккумлятор хэсэг",
      "compatible_cars": ["Prius 30", "Prius 20"],
      "url": "/products/bat-prius30-001",
      "category": "battery"
    }
  ],
  "source": "mock_catalog",
  "rag_snippets": ["Cause hint: ...", "Safety: ..."]
}
```

**Errors**

| Status | Meaning |
| ------ | ------- |
| 400 | Validation error (e.g. empty message, too long). |
| 500 | Internal error (generic message; details logged server-side only). |

---

## `POST /api/intent`

Debug helper returning parsed intent only.

**Request**

```json
{
  "message": "Prius 20 тос хаана байна"
}
```

**Response**

```json
{
  "car_model": "Prius 20",
  "symptom": null,
  "category": "engine_oil",
  "intent_type": "location_check",
  "language": "mn",
  "keywords": ["prius", "20", "тос", "хаана", "байна"]
}
```

---

## `GET /api/products/search`

Debug search over the mock catalog.

**Query parameters**

| Param | Description |
| ----- | ----------- |
| `q` | Free-text query string scored via keywords. |
| `car_model` | Canonical model name (e.g. `Prius 30`). |
| `symptom` | Canonical symptom id (e.g. `won_t_start`). |
| `category` | Category id (e.g. `battery`). |

**Example**

```http
GET /api/products/search?car_model=Prius%2030&symptom=won_t_start&category=battery
```

**Response**

```json
{
  "in_stock": [ { "...product": "fields..." } ],
  "out_of_stock": [ { "...product": "fields..." } ]
}
```

---

## CORS

Allowed origins come from `CORS_ORIGINS` in `backend/.env` (comma-separated). Include every origin that hosts the widget.
