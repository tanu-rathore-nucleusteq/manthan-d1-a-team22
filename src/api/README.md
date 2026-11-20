# ReturnRight API

FastAPI service for the returns portal: order lookup, eligibility, returns, warehouse inspection, finance approval, idempotent refunds, audit log and the manager dashboard.

## Layers

Requests flow down; nothing flows back up.

```
api/v1/endpoints   HTTP only: validate a request DTO, check the role, call one service, return a response DTO
      ↓
services           Use cases and transaction boundaries; write the audit row in the same transaction
      ↓
domain             Pure rules: eligibility, state machine, refund policy, customer flags (no I/O)
repositories       SQLAlchemy queries only
integrations       Outbound HTTP (mock payment gateway), behind the ports in interfaces/
      ↓
models + db        Tables, constraints, sessions
```

Supporting packages: `dtos/` (data transfer objects), `mappers/` (ORM to response DTO), `interfaces/` (ports), `core/` (config, logging, security, errors), `observability/` (metrics, request ids), `utils/` (clock, ids, money).

## DTOs

| Package | What it holds | Built with |
| --- | --- | --- |
| `dtos/requests/` | Inbound API payloads, validated before any service runs; unknown fields rejected | Pydantic v2 (`RequestDTO`) |
| `dtos/responses/` | Outbound API payloads; the frontend builds against these | Pydantic v2 (`ResponseDTO`) |
| `dtos/internal/` | Data passed between services, domain and integrations; never sent over HTTP | Frozen dataclasses |

Enums shared by DTOs, models and rules live in `domain/enums.py`. Money is `Decimal` with two places (`dtos.base.Money`), never `float`.

## Rules every change follows

- Endpoints contain no SQL and no business rules, and return response DTOs, never ORM objects.
- `domain/` imports nothing from FastAPI, SQLAlchemy or other layers, so its tests run in milliseconds.
- Guarantees live in the database where possible: one refund per return item is a unique constraint, not an `if`.
- Services depend on the ports in `interfaces/`, so tests can swap in fakes (for example a gateway that times out).
- Services raise domain errors from `core/exceptions.py`; `api/exception_handlers.py` turns them into HTTP codes.
- Settings come only from environment variables (`core/config.py`); `.env.example` lists them with dummy values.

## Where things go

| You are adding | Put it in |
| --- | --- |
| An endpoint | `api/v1/endpoints/<resource>.py`, mounted in `api/v1/router.py` |
| A request or response shape | `dtos/requests/<resource>.py` or `dtos/responses/<resource>.py` |
| A business rule | `domain/` plus a unit test in `tests/api/unit/` |
| A use case | `services/<area>_service.py` |
| A table or column | `models/` plus an Alembic migration |
| A query | `repositories/<area>_repository.py` |
| ORM to response conversion | `mappers/<area>_mapper.py` |
| A call to another service | a port in `interfaces/`, its client in `integrations/` |
| A metric | `observability/metrics.py` |

## Run and test

From the repository root:

```powershell
pip install -r requirements-dev.txt
docker compose up -d db                                     # PostgreSQL with every table, localhost:5434
cd src/api; python -m scripts.seed; cd ../..                # demo data; add --if-empty to keep existing data
uvicorn mock_gateway.main:app --port 8001 --app-dir src/gateway   # in a second terminal
uvicorn returnright.main:app --reload --app-dir src/api
pytest                                                      # integration tests use the database too
ruff check . ; black --check .                              # before every commit
```

Demo sign-ins after seeding: `warehouse1`, `finance1` and `manager1`, password `DEMO_PASSWORD` (`change-me-demo` unless you set it). The demo orders `ORD-DEMO-01` to `ORD-DEMO-11` belong to `asha.verma@example.com` (01 to 10) and `rohan.mehta@example.com` (11); what each one shows is in `docs/implementation-plan.md` section 7. Set `GATEWAY_DATABASE_URL=postgresql://returnright:change-me@localhost:5434/returnright` for the gateway to keep its payments in the database.

In Docker, `scripts/start.sh` runs the migrations, seeds an empty database and starts the API.

Test names state the rule and the result, for example `test_electronics_day_11_is_refused` and `test_double_refund_click_pays_once`.
