# Backend build phases

The backend is built in two phases so each one ends with working, tested code. Tick an item only when its tests pass. A new session picks up from the first unticked item.

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

## Phase 2: operate, observe and ship (branch `feature/backend-phase-2`)

Goal: the manager's screens, the SRE drill and a one-command start on a fresh clone. Start the branch from `feature/backend-phase-1` (or from `main` once phase 1 is merged).

- [ ] Dashboard endpoints from the SQL views: return rate by category, top reasons, average cycle time, flagged customers
- [ ] Audit endpoints: list with filters, history of one return
- [ ] Seed history: past returns in every state so the dashboard has data
- [ ] One error shape for every 4xx and 5xx (`code`, `message`, `request_id`, field errors)
- [ ] Request IDs on every request and JSON logs
- [ ] Metrics on `/metrics` for the API and the gateway: refund success and failure counts, gateway latency, request rates
- [ ] Docker Compose: API, gateway, web, database, Prometheus and Grafana with a provisioned dashboard and alert rules (refund success below 95%, gateway latency high, database down)
- [ ] CI on GitHub Actions: Ruff, Black, tests with a Postgres service, build the images
- [ ] Locust load test for lookup and refunds
- [ ] Runbook draft for the SRE drill, gateway README as the reusable asset
- [ ] Fresh-clone check: `docker compose up --build` starts everything and the demo works
