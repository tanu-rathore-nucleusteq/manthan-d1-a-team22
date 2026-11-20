# ReturnRight implementation plan (v2)

This plan replaces the PDF build plan. It keeps every feature in the Track A use case and adds the fixes from the plan review. When two documents disagree, the first one in this list wins:

1. `db/schema_v2.sql` (tables and the rules the database enforces)
2. `docs/api-plan.md` and `docs/openapi.json` (the API contract)
3. `CLAUDE.md` (business rules and team decisions)
4. This plan
5. The PDF build plan

## 1. The seven must-haves

| # | Judges ask for | How we build it | Endpoints | Owner | Done when |
| --- | --- | --- | --- | --- | --- |
| 1 | Customer finds an order, picks items, gives a reason, uploads a photo, chooses original payment or store credit | Wizard: find order → pick items with a reason each → photo per item → refund method → review and submit | `POST /orders/lookup`, `POST /returns`, `POST /returns/{code}/photo` | BE-1, FE | A return is saved with a reason per item and a photo stored under `UPLOAD_DIR` |
| 2 | Eligibility engine that explains every answer | Pure function in `domain/eligibility.py`; windows come from the `categories` table | Inside lookup and create | BE-1 | Unit tests pass for day 10/11, day 30/31, innerwear, perishables and a mixed basket. Every refusal has a plain-English reason |
| 3 | QR label and status timeline | QR (SVG, `segno`) holds the return code; the timeline is read from `audit_log` | `GET /returns/{code}/label`, `GET /returns/{code}/timeline`, `POST /returns/{code}/ship` | BE-1, FE | The label prints and the timeline shows the current step |
| 4 | Warehouse scans or types the QR, grades A/B/C, accepts, partly accepts or rejects | One input box for scan or code; grade and decision per item | `GET /warehouse/returns/{code}`, `POST …/receive`, `POST …/inspection` | BE-2, FE | An item is inspected in seconds. Scanning twice shows "already received" |
| 5 | Finance approves refunds above 10,000 INR; refunds go through a mock gateway and a ledger | Return total above 10,000 waits for finance. Gateway key `refund-<return_item_id>`. Insert-only ledger | `GET /finance/approvals`, `POST /finance/approvals/{code}/decision`, `POST /finance/refunds/{id}/pay`, `GET /finance/ledger` | BE-2, FE | Big refunds wait. A double click or a retry pays once. Ledger total equals paid refunds |
| 6 | Dashboard: return rate by category, top reasons, average cycle time, flagged customers | SQL views in `schema_v2.sql` → API → charts | `GET /dashboard`, `/dashboard/return-rates`, `/dashboard/top-reasons`, `/dashboard/flagged-customers` | BE-2 (API), FE (charts) | Numbers match a manual SQL check. Charts use a colour-blind-safe palette and text labels |
| 7 | Every state change in an audit log | Every transition goes through the state machine and writes `audit_log` in the same transaction | `GET /audit`, `GET /audit/returns/{code}` | BE-1 | Each status change has exactly one audit row |

## 2. Business rules and team decisions

| Rule | Exact behaviour |
| --- | --- |
| Return window | Counted from the delivery date, inclusive. Day 30 is allowed, day 31 is refused. Electronics: day 10 allowed, day 11 refused |
| Never returnable | Innerwear and perishables |
| Refund amount | Unit price × quantity × grade percent. Grades A and B pay 100%, grade C pays 50%, a rejected item pays 0 |
| Finance approval | Applies to the return's refund total, strictly above 10,000 INR. 10,000.00 pays automatically; 10,000.01 waits. One decision per return |
| Mixed basket | The wizard shows every item: eligible items in green, ineligible items greyed out with their reason. Only eligible items can be chosen. The API re-checks every item and answers 422 with the reasons if any item is not eligible |
| Frequent returners | More than 3 returns in 30 days: the 4th return flags the customer. Flagged customers can still return; the flag shows on the dashboard |
| Never pay twice | The database allows one refund per return item, and the key `refund-<return_item_id>` goes to the gateway, which stores keys and replays its first answer |
| Store credit | Recorded in the ledger only, with no gateway call. Marked paid straight away |
| Failed payment | A gateway error sets the refund to `failed` and the return stays Inspected. `POST /finance/refunds/{id}/pay` retries with the same key. A timeout is retried the same way; the gateway replays its answer if it already paid |
| Double submit | A bought item can be in only one eligible return (a unique index in the database). A second submit answers 409 |
| Data | Synthetic only: Faker seed 42, 2,000 orders, 40 products in 6 categories, 500 customers |

## 3. Return state machine

| From | To | Trigger | Who |
| --- | --- | --- | --- |
| (new) | Requested | `POST /returns` | Customer |
| Requested | Approved | Same transaction, once every submitted item is confirmed eligible | System |
| Approved | In transit | `POST /returns/{code}/ship` | Customer |
| In transit | Received | `POST /warehouse/returns/{code}/receive` (scan or typed code) | Warehouse agent |
| Received | Inspected | `POST …/inspection` with at least one item accepted | Warehouse agent |
| Received | Rejected | `POST …/inspection` with every item rejected | Warehouse agent |
| Inspected | Refunded | Every accepted item's refund is paid: automatically up to 10,000, after approval above it | System |
| Inspected | Rejected | Finance rejects the refund | Finance reviewer |

Any other move answers 409 "invalid transition". Refunded and Rejected are final. While a refund waits for finance, the return stays Inspected with `awaiting_finance = true`.

Refund statuses: `pending_approval` (return total above 10,000) → `approved` → `processing` → `paid` or `failed`. A failed refund goes back to `processing` on retry with the same key. Store credit goes straight to `paid`. Finance rejection sets `rejected`.

### Failure modes the code and tests must cover

| Failure | Expected behaviour | Guard |
| --- | --- | --- |
| Submit clicked twice | One return; the second call gets 409 | Unique index on eligible return items |
| QR scanned twice | "Already received", nothing changes | State machine (409 shown as a friendly message) |
| Two agents inspect the same return | Only one inspection wins | `returns.version` check and unique inspection per item |
| Refund clicked twice, or retried after a timeout | Paid once | Unique refund per item, gateway idempotency key |
| Gateway returns an error | Refund `failed`, retry pays once | Retry with the same key |
| Finance approves twice | One decision | Unique `finance_approvals.return_id` |
| API asked to jump from Requested to Refunded | 409 invalid transition | State machine |
| Database down | `/health/ready` answers 503, the alert fires, the runbook is followed | Readiness check |

## 4. Who owns each score line

| Score line (points) | Owner | Evidence | Done-check |
| --- | --- | --- | --- |
| Functional (15) | BE-1, BE-2 | The 10 end-to-end cases on the demo seed orders | QA runs all 10 and records results |
| UI/UX (15) | FE | Wizard with stepper, agent screens, dashboard, `docs/ui/` | Phone-width (375 px) and keyboard-only check recorded |
| Claude usage (15) | Everyone; QA curates | `docs/claude-usage.md`: key prompts, corrections, failure modes Claude found. `docs/PROMPTS.md` is logged automatically | At least one entry per person per phase |
| Business alignment (10) | BE-1 | `docs/ideation.md`, business slide in the presentation | Numbers are measured or written as TBD |
| SRE (10) | BE-2, QA | Metrics, Grafana dashboard, alert rule, `docs/runbook.md`, `docs/rca.md` | The alert fires when the gateway is broken, and the runbook was rehearsed once |
| Engineering quality (10) | Everyone; one reviewer per PR | Black, Ruff, ESLint and Prettier clean; tests named by rule and result; reviewed PRs | CI green on main |
| Demo and artifacts (10) | FE drives, QA owns the checklist | `docs/demo-script.md`, the 10 artifacts | One rehearsal and a backup recording |
| Deploy and CI (5) | BE-2 (Compose), QA (CI) | `docker compose up --build` on a fresh clone, `.github/workflows/ci.yml` | Fresh-clone run at 3:15 |
| Security (5) | BE-1 | JWT roles, customer email check, upload type and size checks, no secrets in the repo, `docs/security.md` | 401, 403 and wrong-email tests pass |
| Performance (5) | QA | Locust run, `docs/perf/summary.md` | Results recorded from a real run, never invented |

## 5. Timeline on the event clock

| Time | Whole team | BE-1 | BE-2 | FE | QA |
| --- | --- | --- | --- | --- | --- |
| 0:00–0:20 | Read the card and this plan, confirm owners, start `docs/claude-usage.md` | | | | |
| 0:20–1:00 | Architecture and backlog | `docs/ideation.md`; ask Claude for state-machine failure modes | `docs/lld.md`: context and container diagrams, ledger design, ADR-001 idempotency | Wireframes and refusal wording in `docs/ui/` | `docs/stories.csv`, `docs/test-plan.md`, boundary cases |
| 1:00 | Freeze the API contract (`docs/api-plan.md`, `docs/openapi.json`) | | | | |
| 1:00–2:00 | Vertical slice: one return from lookup to paid refund and ledger row | Seed with demo orders, lookup, eligibility, create return | Gateway `/pay` with idempotency, refund service | Wizard on the real API | Eligibility unit tests |
| 2:00–3:15 | All flows | Label, timeline, audit, flags, security checks | Finance approvals, store credit, failed-payment retry, dashboard API, metrics, all services in Compose | Agent and finance screens, dashboard charts | Duplicate-refund tests, end-to-end cases, CI pipeline, alert rule |
| 3:15 | Fresh clone, `docker compose up --build`, record a backup demo | | | | |
| 3:30 | Feature freeze: only fixes from here | | | | |
| 3:30–4:15 | SRE drill: diagnose, fix, write `docs/rca.md` | | Runbook steps | | Evidence and timeline |
| 4:15–4:45 | Demo and artifacts | Presentation | Explains refund safety | Drives the demo | Shows tests and defects |

## 6. Tasks by role

### BE-1: customer side and core data
1. Seed script `src/api/scripts/seed.py` with the demo orders in section 7 and one staff user per role.
2. `POST /orders/lookup`: order number and email must match; each item has an eligibility answer and reason.
3. Eligibility engine as a pure function, with the boundary tests.
4. `POST /returns`: re-check eligibility, save items with reason and note, Requested → Approved, audit rows, 409 on a duplicate.
5. Photo upload per item: JPEG or PNG only, size limit, random file name.
6. State machine in one place (`domain/state_machine.py`); every transition writes `audit_log`.
7. Label with QR, timeline, mark shipped.
8. Frequent-returner flag on the 4th return in 30 days.
9. Security: customer endpoints check the email; staff endpoints check the JWT role.

### BE-2: money side, gateway and deployment
1. Mock gateway: `POST /pay` with idempotency, its own table, fault switches for delay, error rate and down.
2. Warehouse: receive (scan twice is safe) and inspection per item.
3. Refund service: amount by grade, unique refund per item, gateway call with `refund-<return_item_id>`, ledger row, Inspected → Refunded.
4. Finance: approvals queue, one decision per return, store credit in the ledger only, retry of failed refunds.
5. Dashboard API from the SQL views.
6. `/metrics`: refund success and failure counts, gateway latency.
7. Compose with the API, gateway, web, database, Prometheus and Grafana; Grafana dashboard; runbook.
8. Gateway README as the reusable asset.

### FE: all screens
1. Wireframes and refusal wording first.
2. Staff login (JWT); customer flow without login.
3. Wizard with stepper: green eligible items, greyed ineligible items with the reason.
4. Label page with print button, status timeline.
5. Warehouse screen: one input for scan or code, big A/B/C buttons, keyboard shortcuts.
6. Finance queue: approve or reject, button disabled after the first click.
7. Dashboard charts with a colour-blind-safe palette and labels.
8. Check every page at 375 px and with the keyboard only.

### QA: quality, CI and proof
1. Test plan, test cases and boundary cases (day 10/11, 30/31, grade C, mixed basket, 10,000.00 vs 10,000.01, 3rd vs 4th return).
2. Eligibility tests with BE-1; duplicate-refund tests (double click, two requests at once, retry after timeout) against the real database.
3. The 10 end-to-end cases on the demo orders, key ones automated with Playwright.
4. Defect log with evidence.
5. CI: lint, all tests, build the images.
6. Alert rule (refund success below 95% or gateway latency high) and a rehearsal of breaking the gateway.
7. Locust load test on lookup and refund; results in `docs/perf/summary.md`.
8. Curate `docs/claude-usage.md`.

## 7. Demo seed orders

The seed creates these on top of the random data. Dates are relative to the day the seed runs, so the cases work on any day. All emails use `example.com`.

| Order | Items (category, price) | Delivered | Proves |
| --- | --- | --- | --- |
| `ORD-DEMO-01` | Shirt (Apparel, 1,500) | 5 days ago | Happy path: grade A, full refund, one ledger row |
| `ORD-DEMO-02` | Phone (Electronics, 8,000) | 11 days ago | Refused: electronics window is 10 days |
| `ORD-DEMO-03` | Earbuds (Electronics, 2,500) | 10 days ago | Allowed on day 10 |
| `ORD-DEMO-04` | Vest (Innerwear, 600) | 3 days ago | Refused: never returnable |
| `ORD-DEMO-05` | Jeans (Apparel, 2,200) | 30 days ago | Allowed on day 30 |
| `ORD-DEMO-06` | Jeans (Apparel, 2,200) | 31 days ago | Refused on day 31 |
| `ORD-DEMO-07` | Jacket (Apparel, 2,000) | 5 days ago | Grade C pays 1,000 |
| `ORD-DEMO-08` | Laptop (Electronics, 12,000) | 3 days ago | Waits for finance |
| `ORD-DEMO-09` | Two blenders (Home & Kitchen, 6,000 each) | 4 days ago | Return total 12,000 waits for finance |
| `ORD-DEMO-10` | Phone (Electronics) and shirt (Apparel) | 14 days ago | Mixed basket: shirt allowed, phone refused with a reason |
| `ORD-DEMO-11` | Shoes (Footwear, 3,000), for a customer with 3 returns in the last 30 days | 6 days ago | The 4th return flags the customer |

Staff users: `warehouse1`, `finance1` and `manager1`. Their password comes from the `DEMO_PASSWORD` environment variable, with a dummy value in `.env.example`.

## 8. Artifacts

| # | Artifact | File | Owner | Due |
| --- | --- | --- | --- | --- |
| 1 | Ideation | `docs/ideation.md` | BE-1 | 1:00 |
| 2 | Stories (Excel) | `docs/stories.csv` | QA | 1:00 |
| 3 | LLD | `docs/lld.md` and `docs/adr/` | BE-2 | 1:00 |
| 4 | UI designs | `docs/ui/` (wireframes, then screenshots) | FE | 1:00 and 4:15 |
| 5 | Test plan | `docs/test-plan.md`, `docs/test-cases.csv` | QA | 1:00 |
| 6 | Code base | Repository, `README.md` with one-command run | Everyone | 3:30 |
| 7 | Test results | `docs/test-results.md`, `docs/defects.csv`, `docs/evidence/` | QA | 4:15 |
| 8 | Runbook | `docs/runbook.md`, then `docs/rca.md` after the drill | BE-2 | 3:30 and 4:15 |
| 9 | Application demo | `docs/demo-script.md` and a backup recording | FE | 3:30 |
| 10 | Presentation | `docs/presentation.md` | BE-1 | 4:30 |
| + | Claude usage | `docs/claude-usage.md` (with `docs/PROMPTS.md`) | Everyone, QA curates | From 0:00 |
| + | Reusable asset | `src/gateway/README.md` | BE-2 | 3:30 |

## 9. Changes from the PDF plan

| # | Change | Decision | Status |
| --- | --- | --- | --- |
| 1 | Database driver and load tool | Keep psycopg and Locust. If Smart App Control blocks them on a laptop, run that part in Docker | Decided, no code change |
| 2 | Database port | 5434 (Compose database) | Done |
| 3 | Folder layout | The repository layout: `src/api`, `src/gateway`, `src/web`, `tests/`, `db/`, `docs/`, `deploy/` | Done |
| 4 | Tables | `db/schema_v2.sql` is the source | Done |
| 5 | Finance approval | Per return total, one decision per return | Done in the database and API |
| 6 | State machine wording | Section 3; mixed baskets handled as in section 2 | Done in this plan |
| 7 | Failed payment | `failed` → retry with the same key | Documented in code; BE-2 builds it |
| 8 | Store credit | Ledger only, no gateway | Documented in code; BE-2 builds it |
| 9 | Security | JWT roles for staff, email check for customers, unguessable return codes | In the API stubs; BE-1 builds it |
| 10 | Ship endpoint and double submit | `POST /returns/{code}/ship` exists; duplicate submit answers 409 | Done in the API contract |
| 11 | Demo seed orders | Section 7 | Spec in `seed.py`; BE-1 builds it |
| 12 | Context and container diagrams | Both in `docs/lld.md` | BE-2, due 1:00 |
| + | Enum names | Names match the database codes, values stay lowercase for the API | Done |
| + | Reason and photo | Recorded per returned item, as in the database | Done |

## 10. Definition of done

- [ ] A customer finds an order, returns items with a reason and photo each, chooses a refund method, gets a QR label and sees the timeline
- [ ] Eligibility rules are exact and every refusal has a clear reason
- [ ] The warehouse can scan or type the code, grade A/B/C, and accept, partly accept or reject
- [ ] Refunds above 10,000 INR (return total) wait for finance; grade C pays 50%
- [ ] Refunds are never paid twice: tested with a double click, two requests at once and a retry after a timeout
- [ ] A failed payment can be retried and pays once; store credit never calls the gateway
- [ ] Every status change is in the audit log; the ledger matches the paid refunds
- [ ] The dashboard shows the four views with accessible colours
- [ ] Frequent returners (more than 3 in 30 days) are flagged
- [ ] Seed data: 2,000 orders, 40 products in 6 categories, 500 customers, plus the demo orders
- [ ] Unit tests, duplicate-refund tests, 10 end-to-end cases and the defect log are done
- [ ] `docker compose up --build` works on a fresh clone; CI is green
- [ ] Metrics, Grafana dashboard, alert and runbook are tested by breaking the gateway
- [ ] Context and container diagrams, state machine, ledger design and the idempotency ADR are in `docs/`
- [ ] All 10 artifacts and the Claude usage log are in `docs/`

## 11. Working setup

- Database: `docker compose up -d db`, then connect to `localhost:5434` (database and user `returnright`, password `change-me`).
- API: `uvicorn returnright.main:app --reload --app-dir src/api`, docs at http://127.0.0.1:8000/docs.
- Tests: `pytest` from the repository root.
- After any API change: `python src/api/scripts/generate_api_docs.py`, then commit `docs/api.md` and `docs/openapi.json`.
- Once per clone: `git config core.hooksPath .githooks`, so `docs/COMMITS.md` stays current.
