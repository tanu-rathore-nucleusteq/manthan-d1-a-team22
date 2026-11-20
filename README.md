# ReturnRight

A retail returns and refunds portal. A customer requests a return. The warehouse inspects it, finance approves large refunds, refunds are paid once through a payment gateway, and a manager watches the trends.

Personas: customer, warehouse agent, finance reviewer, operations manager. All data is synthetic.

## Run it (one command)

With Docker Desktop running, from the repository root:

```bash
scripts/start.sh            # Mac, Linux or Git Bash
```

```powershell
.\scripts\start.ps1         # Windows PowerShell
```

The script builds the three images (`returnright-api`, `returnright-gateway`, `returnright-web`), starts them with PostgreSQL, and waits until every container is healthy. It then shows how many rows of demo data each table has and where to sign in. Add `--reset` (`-Reset` in PowerShell) to reload fresh demo data, or `--stop` (`-Stop`) to stop everything and keep the data. Plain `docker compose up --build` does the same start without the summary.

| What | Where |
| --- | --- |
| Web app | http://localhost:8080 |
| API docs (Swagger) | http://localhost:8000/docs |
| Mock payment gateway | http://localhost:8001/health (fault switches at `/admin/faults`) |
| PostgreSQL | `localhost:5434`, database and user `returnright`, password `change-me` |

The database creates its tables from `db/schema_v2.sql`. The API seeds demo data on the first start: 40 products, 500 customers, 2,000 orders and 258 past returns. If a port is taken, set `WEB_PORT`, `API_PORT`, `GATEWAY_PORT` or `DB_PORT` in a `.env` file (see `.env.example`).

## Try the demo

Staff sign-in, password `change-me-demo`:

| User | Role |
| --- | --- |
| `warehouse1` | Warehouse agent |
| `finance1` | Finance reviewer |
| `manager1` | Operations manager |

Customer: email `asha.verma@example.com` with these orders.

| Order | Shows |
| --- | --- |
| `ORD-DEMO-01` | Happy path: grade A, full refund, one ledger row |
| `ORD-DEMO-02` / `-03` | Electronics: refused on day 11, allowed on day 10 |
| `ORD-DEMO-04` | Innerwear is never returnable |
| `ORD-DEMO-05` / `-06` | Allowed on day 30, refused on day 31 |
| `ORD-DEMO-07` | Grade C pays 50% |
| `ORD-DEMO-08` / `-09` | Return totals above 10,000 INR wait for finance |
| `ORD-DEMO-10` | Mixed basket: the shirt is allowed, the phone is refused with a reason |
| `ORD-DEMO-11` (`rohan.mehta@example.com`) | The 4th return in 30 days flags the customer |

To reset the demo data, run `docker compose exec api python -m scripts.seed`.

## Business rules (enforced by the API, each with tests)

- Return windows count from delivery: 30 days as standard, 10 days for electronics. Innerwear and perishables can never be returned. Every refusal says why, in plain words.
- Grades A and B refund 100% and grade C refunds 50%. A return whose refund total is above 10,000 INR needs finance approval.
- A refund is paid once, even after a double click or a retry after a timeout. The database allows one refund per item, the gateway gets the idempotency key `refund-<return_item_id>`, and every paid refund writes exactly one ledger row.
- Statuses go Requested → Approved → In transit → Received → Inspected → Refunded or Rejected. Only allowed moves succeed, and each one writes an audit row in the same transaction.
- A customer with more than 3 returns in 30 days is flagged on the manager dashboard.

## Repository

| Path | What |
| --- | --- |
| `src/api` | FastAPI API: endpoints → services → domain rules and repositories |
| `src/gateway` | Mock payment gateway with fault switches; the reusable asset (see its README) |
| `src/web` | React web app; set `VITE_USE_MOCKS=false` to call the API (the Docker image does) |
| `db/schema_v2.sql` | Database schema, constraints and reporting views |
| `tests/` | API unit and integration tests, gateway tests, end-to-end specs, Locust load test |
| `docs/` | Design, API guides, runbook and plans |

## Tests and checks

```bash
pytest -q                     # all API and gateway tests; integration tests need the database
ruff check . && black --check .
cd src/web && npm run lint && npm run typecheck && npm run build
locust -f tests/load/locustfile.py --host http://127.0.0.1:8000
```

The same checks run on every push and pull request (`.github/workflows/ci.yml`).

## Documentation

- [Frontend API guide](docs/frontend-api-guide.md) and the [generated API reference](docs/api.md)
- [Low-level design](docs/lld.md) and [ADR-001: refund idempotency](docs/adr/0001-refund-idempotency.md)
- [Runbook for the SRE drill](docs/runbook.md)
- [Implementation plan](docs/implementation-plan.md), [backend phases](docs/backend-phases.md) and [end-to-end test cases](docs/e2e-test-cases.md)
