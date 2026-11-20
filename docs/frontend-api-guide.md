# ReturnRight API guide for the frontend

Every API call the web app needs, grouped by screen, with the headers, enum values and error handling. The full field-by-field reference is generated from the code in [api.md](api.md) and [openapi.json](openapi.json); this guide explains how to use it.

## Basics

| Topic | What to do |
| --- | --- |
| Base path | All routes start with `/api/v1`. In dev the Vite proxy forwards `/api` to `http://127.0.0.1:8000`, so call relative paths and leave `VITE_API_BASE_URL` empty |
| Types | Run the API, then `npm run gen:api` in `src/web` to regenerate `src/api/schema.d.ts`. Without a running API: `npx openapi-typescript ../../docs/openapi.json -o src/api/schema.d.ts` |
| Live docs | Swagger UI at http://127.0.0.1:8000/docs |
| Money | Decimal strings with two places, for example `"1499.00"`. Never do arithmetic on them as floats; display them as text |
| Dates | ISO 8601 in UTC: `"2026-11-20T09:30:00Z"` for timestamps, `"2026-12-20"` for dates |
| Lists | `?page=1&size=20` (size up to 100). The answer is `{ items, total, page, size }` |
| Mock or real API | The app uses the in-browser mock unless `VITE_USE_MOCKS=false`; then every call goes through `src/api/httpBackend.ts` to the API |

## Who is calling

| Caller | How they identify | What to send |
| --- | --- | --- |
| Customer | No login. Order number and email prove ownership | Email in the body for `POST /orders/lookup`, `POST /returns` and `POST /returns/{code}/ship`; as the form field `email` for photo uploads; as the header `X-Customer-Email` on every customer GET |
| Warehouse agent, finance reviewer, operations manager | `POST /auth/login` returns a JWT | `Authorization: Bearer <token>` on every staff call (the client middleware in `src/api/client.ts` already adds it) |

The token lasts `expires_in` seconds. On a 401, send the user to the login page. A 403 means the signed-in role can't use that screen.

## Errors

Every error has one shape: `{ "code", "message", "request_id" }`, plus `errors: [{ "field", "message" }]` when fields are invalid. Every response also carries the `X-Request-ID` header; show the id in error messages so support can find the request in the logs (`docs/runbook.md`).

| Status | `code` examples | Meaning |
| --- | --- | --- |
| 401 | `not_authenticated`, `invalid_credentials` | Not signed in, token expired, or a wrong username or password at login |
| 403 | `forbidden` | Signed in with the wrong role |
| 404 | `order_not_found`, `return_not_found`, `not_found` | Order or return not found (for customers: not found for this email) |
| 409 | `invalid_transition`, `already_received`, `duplicate_return`, `already_decided` | Invalid status change, already done, or the item is already in an open return |
| 413 | `photo_too_large` | Photo larger than the limit (5 MB by default) |
| 422 | `validation_error` (with `errors`), `item_not_eligible`, `invalid_date_range` | A field is missing or invalid, or a business rule refused the request |
| 500 | `internal_error` | Our fault; the message never contains internal details |

Show `message`; it is written for customers and staff. For `validation_error`, also highlight the fields named in `errors[].field`. Never retry a write automatically (React Query mutations already use `retry: 0`).

## Enum values and labels

The API sends the lowercase value; show the label.

| Enum | Value → label |
| --- | --- |
| Return status | `requested` Requested · `approved` Approved · `in_transit` In transit · `received` Received · `inspected` Inspected · `refunded` Refunded · `rejected` Rejected |
| Return reason | `damaged` Arrived damaged · `wrong_item` Wrong item sent · `size` Size or fit issue · `not_as_described` Not as described · `changed_mind` Changed my mind · `quality` Poor quality · `other` Other reason |
| Refund method | `original_payment` Original payment · `store_credit` Store credit |
| Grade | `A` Like new · `B` Used, good · `C` Damaged or incomplete (refunds 50%) |
| Inspection decision | `accept` Accept · `reject` Reject |
| Refund status | `pending_approval` Waiting for finance · `approved` Approved · `processing` Paying · `paid` Paid · `failed` Payment failed · `rejected` Rejected |
| Staff role | `warehouse_agent` → `/warehouse` · `finance_reviewer` → `/finance` · `operations_manager` → `/dashboard` |

## Endpoints at a glance

| # | Call | Screen | Status |
| --- | --- | --- | --- |
| 1 | `GET /health` | Status badge | Live |
| 2 | `GET /health/ready` | Status badge | Live |
| 3 | `POST /auth/login` | Staff login | Live |
| 4 | `GET /auth/me` | App shell (who is signed in) | Live |
| 5 | `POST /orders/lookup` | Wizard step 1 | Live |
| 6 | `POST /returns` | Wizard submit | Live |
| 7 | `POST /returns/{code}/photo` | Wizard, after submit | Live |
| 8 | `GET /returns/{code}` | Track my return | Live |
| 9 | `GET /returns/{code}/timeline` | Track my return | Live |
| 10 | `GET /returns/{code}/label` | Label page | Live |
| 11 | `POST /returns/{code}/ship` | Label page / track page | Live |
| 12 | `GET /warehouse/returns` | Warehouse queue | Live |
| 13 | `GET /warehouse/returns/{code}` | Warehouse scan; finance approval detail (names, grades, photos) | Live |
| 14 | `POST /warehouse/returns/{code}/receive` | Warehouse scan | Live |
| 15 | `POST /warehouse/returns/{code}/inspection` | Warehouse inspection | Live |
| 16 | `GET /finance/approvals` | Finance queue | Live |
| 17 | `POST /finance/approvals/{code}/decision` | Finance queue | Live |
| 18 | `GET /finance/refunds` | Finance refunds (filter `failed` for retries) | Live |
| 19 | `GET /finance/refunds/{refund_id}` | Refund details | Live |
| 20 | `POST /finance/refunds/{refund_id}/pay` | Retry a failed refund | Live |
| 21 | `GET /finance/ledger` | Finance ledger | Live |
| 22 | `GET /dashboard` | Manager dashboard (all four views in one call) | Live |
| 23 | `GET /dashboard/return-rates` | Dashboard chart | Live |
| 24 | `GET /dashboard/top-reasons` | Dashboard chart | Live |
| 25 | `GET /dashboard/flagged-customers` | Dashboard table | Live |
| 26 | `GET /audit` | Audit log | Live |
| 27 | `GET /audit/returns/{code}` | Audit for one return | Live |

Every endpoint is live.

## Demo data

After `cd src/api; python -m scripts.seed`, these work against the live API:

- Staff: `warehouse1`, `finance1`, `manager1` with the `DEMO_PASSWORD` (`change-me-demo` by default).
- Customer `asha.verma@example.com`: `ORD-DEMO-01` (happy path) to `ORD-DEMO-10` (mixed basket). `ORD-DEMO-02` is refused (electronics, day 11), `ORD-DEMO-04` is innerwear, `ORD-DEMO-06` is day 31, `ORD-DEMO-08` and `ORD-DEMO-09` need finance approval.
- Customer `rohan.mehta@example.com`: `ORD-DEMO-11`; returning it flags him as a frequent returner.

The full list and what each order shows is in [implementation-plan.md](implementation-plan.md) section 7. Reseed to reset everything.

## Customer screens

### Wizard step 1: find the order

```http
POST /api/v1/orders/lookup
{ "order_number": "ORD-DEMO-01", "email": "asha.verma@example.com" }
```

The answer lists every item with `eligible`, a plain-English `reason` and `window_ends_on`. Show eligible items in green and selectable. Show the others greyed out with the reason, and don't let them be selected. A 404 means the number and email don't match; the message says so without revealing which one is wrong.

### Wizard steps 2 to 4: items, reasons, photos, refund method

Keep everything in component state until the review step. Each chosen item needs a `reason` (and an optional `reason_details`, up to 500 characters). Keep the chosen photo files in memory per `order_item_id`; they are uploaded after the return exists.

### Wizard step 5: submit

```http
POST /api/v1/returns
{
  "order_number": "ORD-DEMO-01",
  "email": "asha.verma@example.com",
  "items": [
    { "order_item_id": 101, "quantity": 1, "reason": "damaged", "reason_details": "Seam torn on arrival" }
  ],
  "refund_method": "store_credit"
}
```

A 201 returns the return with its `return_code` (keep it; every later call uses it) and its `items`, each with `return_item_id` and `order_item_id`. Disable the submit button on the first click. A 409 means one of the items is already in an open return, for example after a double click; show the message and link to that return. A 422 with a `message` means an item is no longer eligible.

### Upload photos

For every item that has a photo, match it by `order_item_id` and upload it with that item's `return_item_id`:

```http
POST /api/v1/returns/{return_code}/photo
Content-Type: multipart/form-data
email=asha.verma@example.com
return_item_id=5001
photo=<JPEG or PNG file, 5 MB at most>
```

The answer has `photo_url`, a path you can put straight into `<img src>`. A 413 means the file is too large.

### Label page

```http
GET /api/v1/returns/{return_code}/label
X-Customer-Email: asha.verma@example.com
```

`qr_svg` is an SVG document: render it inside the page, for example with an `<img>` whose `src` is `data:image/svg+xml;utf8,` plus the URL-encoded SVG. `ship_to` is the warehouse address. Add a print button (`window.print()`). Then offer "I've shipped it":

```http
POST /api/v1/returns/{return_code}/ship
{ "email": "asha.verma@example.com" }
```

A 409 means the return isn't in the Approved state, for example it was already marked shipped.

### Track my return

```http
GET /api/v1/returns/{return_code}
X-Customer-Email: asha.verma@example.com
```

The detail includes `status`, the items (with grade, decision and refund amount once inspected) and `timeline`, oldest first. `GET /returns/{code}/timeline` returns only the timeline, for polling. Draw the stepper from the seven statuses: Requested → Approved → In transit → Received → Inspected → Refunded, with Rejected as the alternative last step. While a big refund waits for finance, the status stays `inspected`.

## Staff screens

### Login

```http
POST /api/v1/auth/login
{ "username": "warehouse1", "password": "<DEMO_PASSWORD>" }
```

The answer is `{ access_token, token_type: "bearer", expires_in, role }`. Store the token and send the user to the page for their `role`. `GET /auth/me` returns `{ user_id, username, role }` for the app shell. Demo users after seeding: `warehouse1`, `finance1`, `manager1`.

### Warehouse

1. Queue: `GET /warehouse/returns?status=in_transit` returns `ReturnSummaryResponse` rows with `customer_name` and `order_number`. `customer_flagged` marks frequent returners.
2. Scan: one text box that accepts a scanner (scanners type the code and press Enter) or a typed code. Then `GET /warehouse/returns/{code}`. Staff detail adds `customer_name` and `customer_flagged`; every item has `unit_price`, so the screen can preview the refund (grade C pays 50%).
3. Receive: `POST /warehouse/returns/{code}/receive`. A 409 on a second scan means it was already received; show "Already received" and continue to inspection.
4. Inspect: one grade (A/B/C) and one decision per item, with keyboard shortcuts for speed.

```http
POST /api/v1/warehouse/returns/{return_code}/inspection
{ "items": [ { "return_item_id": 5001, "grade": "C", "decision": "accept", "notes": "Scuffed sole" } ] }
```

The answer has the refund amount per item, `refund_total` and `needs_finance_approval`. When it is true, tell the agent the refund is waiting for finance. A 409 means another agent inspected it first; reload the return.

### Finance

1. Queue: `GET /finance/approvals` lists returns whose refund total is above 10,000 INR, with their refunds and `customer_flagged`.
2. Decide: `POST /finance/approvals/{return_code}/decision` with `{ "approve": true, "comment": "Photo matches" }`. Disable both buttons on the first click. A 409 means it was already decided.
3. Failed payments: `GET /finance/refunds?status=failed`. Retry one with:

```http
POST /api/v1/finance/refunds/{refund_id}/pay
Idempotency-Key: 6f1d2c1e-7b8a-4c4e-9a51-2f0c1c7e9d10
```

Create the key with `crypto.randomUUID()` when the reviewer clicks Retry, and reuse the same key if that request times out or the page retries it. The refund is never paid twice either way.

4. Ledger: `GET /finance/ledger` (optionally `?refund_id=`) lists `refund` rows (positive) and `reversal` rows (negative), each with the method and gateway reference.

### Operations manager

`GET /dashboard?date_from=2026-11-01&date_to=2026-11-30` returns all four views in one call: `return_rate_by_category` (`orders`, `returns` and `return_rate` as a fraction, 0.125 = 12.5%), `top_reasons` (every reason used, most first), `average_cycle_time_hours` (`null` when no return has closed) and `flagged_customers`. Both dates are optional and inclusive. The web app draws the charts from these numbers. The three smaller dashboard calls return one view each if a chart refreshes on its own. Use a colour-blind-safe palette and put the value as text on every bar.

`GET /audit?entity=return&page=1` lists audit entries newest first (`entity` is `return`, `refund` or `customer`; add `entity_id` for one record). `GET /audit/returns/{code}` lists everything recorded for one return, oldest first: status changes, payment attempts and finance decisions, each with `action`, `from_status`, `to_status`, `actor` and `actor_role`.

## Rules the screens must follow

- Never let a refused item be selected; always show its reason.
- Disable every write button on the first click: submit, ship, receive, inspect, approve, reject, retry.
- Never invent statuses on the client: show what the API returns and reload after each action.
- Every page must work at 375 px wide and with the keyboard only.
