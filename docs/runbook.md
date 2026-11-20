# ReturnRight runbook

For whoever is on call during the SRE drill. Each incident lists how to spot it, what to do, and how to confirm it is fixed. Commands run from the repository root with the stack started by `docker compose up --build`.

## Where to look

| What | How |
|---|---|
| Is everything up? | `docker compose ps` (every service `healthy`) |
| API readiness | `curl http://localhost:8000/api/v1/health/ready` → `status` is `ok`, `degraded` (gateway down, returns still work) or `down` (database down, HTTP 503) |
| Gateway and its fault switches | `curl http://localhost:8001/health` and `curl http://localhost:8001/admin/faults` |
| Failed refunds | Finance screen, or `GET /api/v1/finance/refunds?status=failed` as `finance1` |
| One user's error | Every error body and response carries `request_id`; run `docker compose logs api \| grep <request_id>` |
| Logs | `docker compose logs -f api` (one JSON line per request: method, path, status, duration_ms, request_id) |
| Money check | `docker compose exec db psql -U returnright -c "SELECT * FROM v_ledger_check"` must return 0 rows |

Prometheus, Grafana and automatic alerts arrive in phase 3 (`docs/backend-phases.md`). Until then, the checks above are the alerts.

## Incident 1: payment gateway down

**Signs:** readiness shows `"gateway": "down"` or `"degraded"`; refunds stay `failed`; API logs show requests to `/inspection`, `/decision` or `/pay` completing while refunds fail; gateway logs show 503.

**Do:**
1. Check the gateway: `curl http://localhost:8001/health` and `curl http://localhost:8001/admin/faults`.
2. If a fault switch is on (drill), turn it off: `curl -X POST http://localhost:8001/admin/faults -H "Content-Type: application/json" -d '{"latency_ms": 0, "error_rate": 0, "down": false}'`.
3. If the container is unhealthy, restart it: `docker compose restart gateway`.
4. Retry each failed refund from the finance screen (or `POST /api/v1/finance/refunds/{refund_id}/pay` with an `Idempotency-Key` header). The gateway key is always `refund-<return_item_id>`, so a retry never pays twice.

**Confirm:** the refunds are `paid`, the return moves to `refunded`, and `v_ledger_check` returns 0 rows.

## Incident 2: gateway slow or failing some requests

**Signs:** refunds take seconds; some refunds `failed` after the API's automatic retries (2 retries, 2-second timeout); gateway logs show 502s or slow responses.

**Do:** read `/admin/faults`, then set `latency_ms` and `error_rate` back to 0 (drill), or restart the gateway. Retry failed refunds as in incident 1. A payment that timed out on our side was still recorded by the gateway; the retry gets the same answer back instead of a second payment.

**Confirm:** a new refund pays in under a second; `v_ledger_check` returns 0 rows.

## Incident 3: database down

**Signs:** readiness returns HTTP 503 with `"database": "down"`; every screen shows "Something went wrong on our side" (`internal_error`); `docker compose ps` shows `db` unhealthy or exited.

**Do:** `docker compose start db` (or `docker compose restart db`), wait until it is healthy, then `docker compose restart api` if the API keeps failing.

**Confirm:** readiness is `ok`; the warehouse queue loads; a test order lookup works (`ORD-DEMO-01`, `asha.verma@example.com`).

## Incident 4: one customer or agent reports an error

1. Ask for the message on screen and the time. Error responses carry a `request_id`; the browser's network tab shows it in the `X-Request-ID` header.
2. `docker compose logs api | grep <request_id>` shows the request and any stack trace (`"level": "ERROR"`).
3. Errors with a `code` such as `item_not_eligible`, `invalid_transition` or `already_received` are expected answers, not faults; explain them to the user.

## After the drill

- Turn every fault switch off and check readiness is `ok`.
- Run the money check (`v_ledger_check`: 0 rows).
- Reset the demo data if needed: `docker compose exec api python -m scripts.seed` (deletes and reloads all data).
- Write the timeline, cause and fix in `docs/rca.md`.
