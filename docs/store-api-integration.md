# Store API integration guide

This MVP ships with **`MockStoreClient`**, which reads:

- `backend/data/products.json` — catalog, compatibility, symptoms, pricing, stock, shelf location.
- `backend/data/car_aliases.json` — maps nicknames to canonical vehicle names for intent parsing.
- `backend/data/symptom_map.json` — troubleshooting hints consumed like lightweight RAG snippets.

To go live against your commerce stack, replace the mock adapter with real HTTP calls inside **`RestStoreClient`** (`backend/app/store_client.py`).

---

## 1. Configuration

In `backend/.env`:

```env
STORE_PROVIDER=rest
STORE_API_URL=https://api.your-store.example
STORE_API_KEY=...
STORE_API_TIMEOUT=10
```

`STORE_PROVIDER` selects the adapter in `build_store_client(...)`.

---

## 2. Responsibilities of the REST adapter

Implement these methods against your backend (Laravel REST, ERP middleware, etc.):

| Method | Purpose |
| ------ | ------- |
| `search_products(...)` | Search catalog by text + structured filters (car, symptom code, category id). Should return the **same shape** as rows in `products.json` so the orchestrator and widget stay unchanged. |
| `get_product_detail(product_id)` | Optional enrichment for detail pages. |
| `check_stock(product_id)` | Authoritative stock figure for validation-heavy flows. |
| `get_product_location(product_id)` | Shelf / aisle / branch encoding as plain text or structured JSON mapped to text. |

**Do not** simulate fake HTTP responses—wire real endpoints when credentials exist; raise clear errors until configured.

---

## 3. Suggested Laravel-side endpoints

Typical mapping (adjust to your API design):

| Concern | Example route |
| ------- | --------------- |
| Catalog search | `GET /api/v1/products/search?q=&car=&symptom=&category=` |
| Inventory | `GET /api/v1/products/{id}/stock` |
| Location | `GET /api/v1/products/{id}/location` |

Return stable ids matching web URLs (`url` field) so the widget’s product cards deep-link correctly.

---

## 4. Keeping answers grounded

1. **Never** let the LLM invent numeric inventory—always inject **exact** JSON from your APIs into the prompt (already enforced by prompt rules).  
2. Extend **`validators.py`** if your compliance rules require SKU-level regex checks or rounding rules for displayed prices.  
3. If search returns zero rows, the orchestrator already guides staff escalation—keep that behavior for trust.

---

## 5. Incremental rollout

1. Keep `products.json` as a fallback cache or shadow comparison dataset.  
2. Implement `search_products` first (widest impact).  
3. Split inventory vs catalog if your commerce API separates concerns—mirror that in dedicated tool modules later without changing the widget contract.
