# Mock payment gateway

A small, separate FastAPI service that stands in for a real payment provider. It is our reusable asset: any team that needs to demo or test payments, retries and failure handling can copy this folder.

## What it does

| Endpoint | Purpose |
| --- | --- |
| `POST /payments` | Pays a refund. Requires an `Idempotency-Key` header; a repeated key returns the original answer with `"replayed": true` and never pays twice. The same key with a different amount answers 409 |
| `GET /admin/faults` | Shows the current fault switches |
| `POST /admin/faults` | Changes the fault switches at runtime: latency, error rate, outage |
| `GET /health` | Liveness check |
| `GET /metrics` | Prometheus metrics (added in backend phase 2) |

```http
POST /payments
Idempotency-Key: refund-5001
{ "refund_id": 42, "amount": "1500.00", "currency": "INR" }

200 { "transaction_id": "gw_3f9c0a1b2c3d4e5f", "status": "succeeded", "amount": "1500.00", "replayed": false }
```

## Fault switches

Set them in `.env` (see `.env.example`) or change them live:

```powershell
curl -X POST http://127.0.0.1:8001/admin/faults -H "Content-Type: application/json" -d '{"latency_ms": 3000, "error_rate": 0.5, "down": false}'
```

| Switch | Effect |
| --- | --- |
| `GATEWAY_LATENCY_MS` / `latency_ms` | Delay added after the payment is recorded, so a client that times out has still been paid and its retry gets the replayed answer |
| `GATEWAY_ERROR_RATE` / `error_rate` | Share of requests (0.0 to 1.0) that answer 502 without paying; a retry with the same key can succeed |
| `GATEWAY_DOWN` / `down` | Every request answers 503 without paying, as if the provider were offline |

Use them to rehearse the SRE drill: turn on latency, errors or an outage, watch the alert fire, follow the runbook, then turn it off. If `GATEWAY_ADMIN_TOKEN` is set, `POST /admin/faults` needs the `X-Admin-Token` header.

## Where payments are kept

`GATEWAY_DATABASE_URL` points at PostgreSQL; the service creates `gateway.payments` on start-up if it is missing. Leave it empty to keep payments in memory, which needs no database but forgets every key on restart.

## Run

```powershell
uvicorn mock_gateway.main:app --port 8001 --app-dir src/gateway   # from the repo root
```

Tests: `pytest tests/gateway`.

## Adopting it in another project

Copy `src/gateway/`, build it with its `Dockerfile`, and point your service's payment client at it. Send a unique idempotency key per payment, reuse the same key on every retry, and treat 502, 503 and timeouts as "retry later with the same key".
