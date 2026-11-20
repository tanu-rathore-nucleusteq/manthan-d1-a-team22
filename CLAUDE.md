# ReturnRight · notes for Claude

Track A of AI Manthan Wave 1. A returns portal: customer request → warehouse inspection → finance approval → refund, plus a manager dashboard.
Personas: customer, warehouse agent, finance reviewer, operations manager.

When documents disagree, the first one wins: `db/schema_v2.sql` → `docs/api-plan.md` (and `docs/openapi.json`) → this file → `docs/implementation-plan.md`.

## Stack (never use APIs from older major versions)
- Python 3.13 · FastAPI · SQLAlchemy 2.0 + psycopg 3 · Pydantic v2 · Alembic · pytest · Locust
- React 19 + Vite + TypeScript · Playwright
- PostgreSQL 18 in Docker Compose on `localhost:5434`, tables from `db/schema_v2.sql`. The mock payment gateway is a separate FastAPI service.
- Prometheus + Grafana for metrics, dashboard and alert rules.
- Layout: `src/api/returnright`, `src/gateway/mock_gateway`, `src/web`, `tests/api/{unit,integration}`, `tests/gateway`, `tests/e2e`, `db/`, `docs/`, `deploy/`.

## Backend rules
- Layers (see `src/api/README.md`): endpoints are HTTP only → services own use cases, transactions and audit rows → domain holds pure rules with no I/O · repositories hold SQL only · integrations hold the gateway client. Never put SQL or business rules in endpoints.
- Endpoints take request DTOs and return response DTOs (`returnright/dtos/`), never ORM objects.
- Enums live in `domain/enums.py`. Member names are the exact database codes; values are the lowercase strings the API and frontend use. Map columns with `Enum(<EnumClass>, native_enum=False)`, which stores the names.
- Money is `Decimal`, never `float`.
- API conventions: staff use a JWT with a role claim (`require_role`); customers prove ownership with order number and email, then the `X-Customer-Email` header. 409 is an invalid transition or a duplicate, 422 is bad input or an ineligible item.
- After any API change, run `python src/api/scripts/generate_api_docs.py` and commit `docs/api.md` and `docs/openapi.json`.

## Domain rules (enforced on the server, each with a test)
- Window counted from the delivery date, inclusive: day 30 allowed, day 31 refused. Electronics: day 10 allowed, day 11 refused. Innerwear and perishables are never returnable.
- The eligibility engine is a pure function that returns eligible or not plus a plain-English reason per item.
- Grades A and B refund 100%, grade C 50%, a rejected item 0. Reason, note and photos are recorded per returned item.
- Finance approval applies to the return's refund total, strictly above 10,000 INR. One decision per return.
- Mixed basket: only eligible items can be submitted; the API re-checks and answers 422 with reasons otherwise.
- More than 3 returns in 30 days flags the customer. Flagged customers can still return.
- Refunds are idempotent: one refund per return item in the database, and `refund-<return_item_id>` as the gateway idempotency key.
- A failed payment sets the refund to `failed`; a retry uses the same key. Store credit goes to the ledger only, never the gateway.
- States: Requested → Approved → In transit → Received → Inspected → Refunded | Rejected. Only allowed transitions succeed (409 otherwise). Every state change writes an `audit_log` row in the same transaction.
- Synthetic data only: Faker seed 42, 2,000 orders, 40 products in 6 categories, 500 customers, plus the demo orders in `docs/implementation-plan.md`.
- Refusals use plain, friendly text that says why and what the customer can do instead.

## Engineering standards (evaluators check the repository)
- Short-lived `feature/` and `fix/` branches; merge to `main` through a reviewed pull request.
- Commits: imperative, one change each, prefixed `feat|fix|test|docs|ci|chore`.
- Black + Ruff and Prettier + ESLint pass before commit. No unused or commented-out code.
- snake_case in Python and SQL, camelCase in TypeScript, PascalCase for classes.
- Test names state the rule and the result: `test_electronics_day_11_is_refused`.
- One command runs all tests. No secrets in the repository; `.env.example` holds dummy values.

## Commands
- Database: `docker compose up -d db`
- API: `uvicorn returnright.main:app --reload --app-dir src/api` (docs at http://127.0.0.1:8000/docs)
- Gateway: `uvicorn mock_gateway.main:app --port 8001 --app-dir src/gateway`
- Tests from the repository root: `pytest -q`, or `pytest -q -x <path>` for one area. Lint: `ruff check .` and `black --check .`

## Working with Claude
- Plan first, then build one story at a time; run the affected tests before each commit.
- Record key prompts, corrections and failure modes Claude found in `docs/claude-usage.md`.
- Never invent numbers for documents or the presentation: write TBD.
