# Backend build phases

The backend is built in phases so each one ends with working, tested code. Tick an item only when its tests pass. A new session picks up from the first unticked item.

## Phase 1: every flow works end to end (branch `feature/backend-phase-1`)

Goal: a customer return goes from order lookup to a paid refund and a ledger row against the real database, for all four personas except the manager's read screens.

- [x] Architecture docs: ADR-001 on idempotency and per-return approval (`docs/adr/`), context and container diagrams, state machine and ledger design (`docs/lld.md`)
- [x] ORM models for every table in `db/schema_v2.sql`
- [x] Domain rules: category eligibility (electronics 10 days, innerwear and perishables never), state machine, refund policy (grades, 50%, threshold on the return total), frequent-returner flag
- [x] Staff login: bcrypt passwords, JWT with a role claim, `GET /auth/me`, role checks on staff routes
- [x] Seed script: 40 products in 6 categories, 500 customers, 2,000 orders, staff users, the demo orders from `docs/implementation-plan.md` section 7
- [x] Mock gateway: `POST /payments` with idempotency keys, fault switches (latency, error rate, outage) from the environment and `POST /admin/faults`, Postgres or in-memory store
- [x] Returns: create (eligibility re-check, 422 with reasons, 409 on a double submit, flag check), photo upload per item (type and size checks), detail, timeline, QR label, mark shipped, customer email check
- [x] Warehouse: queue, scan, receive (scanning twice answers "already received"), inspection per item with refund amounts and optimistic locking
- [x] Refunds: one refund per item, gateway key `refund-<return_item_id>`, retries with the same key, `failed` → retry → `paid`, store credit to the ledger only, ledger row per paid refund, return closed when every refund is paid
- [x] Finance: approvals queue, one decision per return, refunds list and detail, retry endpoint, ledger
- [x] Tests: unit tests for every rule; integration tests through the API on the real database for the happy path, grade C, two 6,000 items, double submit, failed payment retry, double pay, store credit, scanning twice, the 4th return and a wrong email
- [x] API docs regenerated; the frontend guide marks the phase 1 endpoints live

Verified on 2026-11-20: 124 tests pass (unit, gateway and integration on the real database, each integration test rolled back), Ruff and Black are clean, and a live run of the API and the mock gateway over HTTP passed 21 demo checks, including a gateway outage, a retry that paid once, and the ledger reconciliation view staying empty.

## Phase 2: manager screens, errors, logs and one-command start (branch `feature/backend-phase-2`)

Goal: the manager's screens on real data, one error shape, traceable logs, and a one-command start on a fresh clone. The web app draws the dashboard charts itself from `GET /dashboard`, so Prometheus and Grafana moved to phase 3.

- [x] Dashboard endpoints: return rate by category (orders and returns per category), top reasons, average cycle time, flagged customers, optional date range; computed in SQL in the shape the web dashboard already reads
- [x] Audit endpoints: list with entity filters (newest first), everything recorded for one return (oldest first)
- [x] Seed history: 258 closed past returns (refunded with grades A, B and C, store credit and original payment, finance-approved above 10,000; some rejected), three flagged customers; queues stay clear for the demo
- [x] One error shape for every 4xx and 5xx (`code`, `message`, `request_id`, `errors` per field for invalid input); no internal details on a 500
- [x] Request IDs on every request (caller's `X-Request-ID` when safe, otherwise generated) and JSON logs, one line per request
- [x] Staff fields the screens need: customer name and order number on queue rows and staff detail, unit price per item, customer flag on staff detail only
- [x] Web app talks to the real API with `VITE_USE_MOCKS=false` (`src/web/src/api/httpBackend.ts`); mocks stay the default
- [x] Docker Compose: database, gateway, API and web (nginx proxying `/api`) with health checks; `docker compose up --build`
- [x] CI on GitHub Actions: Ruff, Black, tests with a Postgres service, web lint, typecheck and build, image builds
- [x] Locust load test for lookup, dashboard and refunds (`tests/load/locustfile.py`)
- [x] Runbook draft for the SRE drill (`docs/runbook.md`); gateway README as the reusable asset
- [x] Fresh-clone check: the stack started from images, health, web proxy, staff login and order lookup answered 200

## Phase 3: observability and hardening

- [ ] Metrics on `/metrics` for the API and the gateway: refund success and failure counts, gateway latency, request rates
- [ ] Prometheus and Grafana in Docker Compose with a provisioned dashboard and alert rules (refund success below 95%, gateway latency high, database down)
- [ ] A "Live metrics" button on the manager dashboard that opens Grafana in a new tab
- [ ] Regenerate `src/web/package-lock.json` on Linux, then switch CI and the web Dockerfile back to `npm ci`
- [ ] Send staff to the login page when a token expires (401)
- [ ] Align the web app's reason codes with the API (`size`, `changed_mind`, `quality`) instead of mapping them in `httpBackend.ts`
- [ ] Refunds while the gateway is down: today the refund is marked failed and finance retries it from the failed-refunds list; add an automatic retry once the gateway is back
