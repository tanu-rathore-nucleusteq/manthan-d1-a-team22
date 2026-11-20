# Mock payment gateway

A small, separate FastAPI service that stands in for a real payment provider. It is our reusable asset: any team that needs to demo or test payments, retries and failure handling can copy this folder.

## What it does

| Endpoint | Purpose |
| --- | --- |
| `POST /payments` | Pays a refund. Requires an `Idempotency-Key` header; a repeated key returns the original result and never pays twice |
| `POST /admin/faults` | Changes the fault switches at runtime: latency, error rate, outage |
| `GET /health` | Liveness check |
| `GET /metrics` | Prometheus metrics: payments by result, idempotent replays, request latency |

Processed keys are stored in the `gateway.payments` table (`GATEWAY_DATABASE_URL`, see `.env.example`). The insert is atomic, so two requests with the same key at the same moment pay once, and a key is still recognised after the gateway restarts. Reusing a key for a different refund or amount returns `409`.

## Fault switches

Set them in `.env` (see `.env.example`) or change them live with `POST /admin/faults`:

- `GATEWAY_LATENCY_MS`: delay added to every payment
- `GATEWAY_ERROR_RATE`: share of payments that fail, from 0.0 to 1.0
- `GATEWAY_DOWN`: when true, every payment fails as if the provider were offline

Use them to rehearse the SRE drill: turn on latency or an outage, watch the alert fire, then turn it off.

## Run

```powershell
uvicorn mock_gateway.main:app --port 8001 --app-dir src/gateway   # from the repo root
```

## Adopting it in another project

Copy `src/gateway/`, build it with its `Dockerfile`, and point your service's payment client at it. Send a unique idempotency key per payment and reuse the same key on every retry.
