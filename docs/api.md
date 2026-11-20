# ReturnRight API

The ReturnRight API has 27 endpoints under `/api/v1`, for customers, warehouse agents, finance reviewers and operations managers. 2 are implemented; the rest are typed stubs that validate input and return `501` until their story lands.

Generated from the FastAPI app on 2026-11-20 by `python src/api/scripts/generate_api_docs.py`. Do not edit by hand: change the code, then regenerate. The design behind it is in [api-plan.md](api-plan.md).

## Basics

| Topic | How it works |
| --- | --- |
| Base URL | `http://127.0.0.1:8000/api/v1` locally |
| Interactive docs | `/docs` (Swagger UI), `/redoc`, and the raw schema at `/openapi.json` (copy: [openapi.json](openapi.json)) |
| Staff sign-in | `POST /api/v1/auth/login` returns a JWT. Send it as `Authorization: Bearer <token>`. Each staff route accepts one role |
| Customers | No login. The order number plus email proves ownership. Later calls on a return send the email in `X-Customer-Email`, or in the body for actions |
| Refund idempotency | `POST /finance/refunds/{refund_id}/pay` needs an `Idempotency-Key` header. Send the same key on every retry; a refund is never paid twice |
| Pagination | `?page=1&size=20` (size ≤ 100) on list endpoints, returning `items`, `total`, `page`, `size` |
| Money | Decimal strings with two places, in INR, for example `"1499.00"`. Never floats |
| Dates | ISO 8601: `2026-11-20` for dates, `2026-11-20T10:30:00Z` (UTC) for timestamps |
| Request bodies | Strict: unknown fields are rejected with `422`; strings are trimmed |

## Errors

Every error has a JSON body. Today it is FastAPI's `{"detail": ...}`; the planned `ErrorResponse` (`code`, `message`, `request_id`) replaces it when the exception handlers land.

| Status | When |
| --- | --- |
| 401 | Staff route without a valid bearer token |
| 403 | Signed in, but with a role this route does not accept |
| 404 | The order or return does not exist, or the email does not match |
| 409 | The return is not in the state this action needs (invalid transition), or the refund is already decided or paid |
| 413 | Uploaded photo is larger than `UPLOAD_MAX_MB` |
| 422 | Input failed validation, or an item is not eligible for return; the body says which field and why |
| 501 | The endpoint is planned but not implemented yet |
| 503 | `/health/ready` only: the database is down |

A `422` validation body looks like this:

```json
{
  "detail": [
    {
      "type": "string_pattern_mismatch",
      "loc": ["body", "email"],
      "msg": "String should match pattern '^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$'",
      "input": "not-an-email"
    }
  ]
}
```

## Endpoints at a glance

| # | Method | Path | What it does | Access | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | GET | [`/api/v1/health`](#op-get-api-v1-health) | Liveness: the API process is up | Public | Done |
| 2 | GET | [`/api/v1/health/ready`](#op-get-api-v1-health-ready) | Readiness: PostgreSQL and the payment gateway answer | Public | Done |
| 3 | POST | [`/api/v1/auth/login`](#op-post-api-v1-auth-login) | Sign in and receive a JWT | Public | Stub |
| 4 | GET | [`/api/v1/auth/me`](#op-get-api-v1-auth-me) | The signed-in user and role | Any staff role | Stub |
| 5 | POST | [`/api/v1/orders/lookup`](#op-post-api-v1-orders-lookup) | Find an order and explain which items can be returned | Customer (no login) | Stub |
| 6 | POST | [`/api/v1/returns`](#op-post-api-v1-returns) | Request a return for one or more items | Customer (no login) | Stub |
| 7 | POST | [`/api/v1/returns/{return_code}/photo`](#op-post-api-v1-returns-return-code-photo) | Upload a photo of the item (JPEG or PNG, stored locally) | Customer (no login) | Stub |
| 8 | GET | [`/api/v1/returns/{return_code}`](#op-get-api-v1-returns-return-code) | Return details | Customer (no login) | Stub |
| 9 | GET | [`/api/v1/returns/{return_code}/timeline`](#op-get-api-v1-returns-return-code-timeline) | Status timeline: Requested → … → Refunded or Rejected | Customer (no login) | Stub |
| 10 | GET | [`/api/v1/returns/{return_code}/label`](#op-get-api-v1-returns-return-code-label) | Mock return label with a QR code | Customer (no login) | Stub |
| 11 | POST | [`/api/v1/returns/{return_code}/ship`](#op-post-api-v1-returns-return-code-ship) | Customer confirms the parcel is shipped (Approved → In transit) | Customer (no login) | Stub |
| 12 | GET | [`/api/v1/warehouse/returns`](#op-get-api-v1-warehouse-returns) | Work queue of returns, filtered by status | Warehouse agent | Stub |
| 13 | GET | [`/api/v1/warehouse/returns/{return_code}`](#op-get-api-v1-warehouse-returns-return-code) | Find a return by its QR code | Warehouse agent | Stub |
| 14 | POST | [`/api/v1/warehouse/returns/{return_code}/receive`](#op-post-api-v1-warehouse-returns-return-code-receive) | Mark the parcel received (In transit → Received) | Warehouse agent | Stub |
| 15 | POST | [`/api/v1/warehouse/returns/{return_code}/inspection`](#op-post-api-v1-warehouse-returns-return-code-inspection) | Grade each item A, B or C and accept or reject it (Received → Inspected) | Warehouse agent | Stub |
| 16 | GET | [`/api/v1/finance/approvals`](#op-get-api-v1-finance-approvals) | Returns whose refund total is above the approval threshold | Finance reviewer | Stub |
| 17 | POST | [`/api/v1/finance/approvals/{return_code}/decision`](#op-post-api-v1-finance-approvals-return-code-decision) | Approve or reject a refund above the threshold | Finance reviewer | Stub |
| 18 | GET | [`/api/v1/finance/refunds`](#op-get-api-v1-finance-refunds) | Refunds by status | Finance reviewer | Stub |
| 19 | GET | [`/api/v1/finance/refunds/{refund_id}`](#op-get-api-v1-finance-refunds-refund-id) | One refund | Finance reviewer | Stub |
| 20 | POST | [`/api/v1/finance/refunds/{refund_id}/pay`](#op-post-api-v1-finance-refunds-refund-id-pay) | Pay an approved refund through the gateway (idempotent) | Finance reviewer | Stub |
| 21 | GET | [`/api/v1/finance/ledger`](#op-get-api-v1-finance-ledger) | Ledger of gateway refunds and store credit | Finance reviewer | Stub |
| 22 | GET | [`/api/v1/dashboard`](#op-get-api-v1-dashboard) | All dashboard metrics in one call | Operations manager | Stub |
| 23 | GET | [`/api/v1/dashboard/return-rates`](#op-get-api-v1-dashboard-return-rates) | Return rate by category | Operations manager | Stub |
| 24 | GET | [`/api/v1/dashboard/top-reasons`](#op-get-api-v1-dashboard-top-reasons) | Top return reasons | Operations manager | Stub |
| 25 | GET | [`/api/v1/dashboard/flagged-customers`](#op-get-api-v1-dashboard-flagged-customers) | Customers with more than 3 returns in 30 days | Operations manager | Stub |
| 26 | GET | [`/api/v1/audit`](#op-get-api-v1-audit) | Audit log, newest first | Operations manager | Stub |
| 27 | GET | [`/api/v1/audit/returns/{return_code}`](#op-get-api-v1-audit-returns-return-code) | Every state change of one return, oldest first | Operations manager | Stub |

## Health

<a id="op-get-api-v1-health"></a>
### `GET /api/v1/health`

Liveness: the API process is up

**Access:** Public · **Status:** Implemented

| Status | Meaning | Body |
| --- | --- | --- |
| 200 | Success | [`LivenessResponse`](#model-livenessresponse) |

Example response:

```json
{
  "status": "ok"
}
```

<a id="op-get-api-v1-health-ready"></a>
### `GET /api/v1/health/ready`

Readiness: PostgreSQL and the payment gateway answer

**Access:** Public · **Status:** Implemented

| Status | Meaning | Body |
| --- | --- | --- |
| 200 | Success | [`HealthResponse`](#model-healthresponse) |
| 503 | The database is down | [`HealthResponse`](#model-healthresponse) |

Example response:

```json
{
  "status": "ok",
  "database": "ok",
  "gateway": "ok"
}
```

## Auth

<a id="op-post-api-v1-auth-login"></a>
### `POST /api/v1/auth/login`

Sign in and receive a JWT

**Access:** Public · **Status:** Stub: returns 501

**Request body:** [`LoginRequest`](#model-loginrequest)

```json
{
  "username": "warehouse1",
  "password": "demo-password"
}
```

| Status | Meaning | Body |
| --- | --- | --- |
| 200 | Success | [`TokenResponse`](#model-tokenresponse) |
| 422 | Validation Error | [`HTTPValidationError`](#model-httpvalidationerror) |
| 501 | Planned, not implemented yet | `{"detail": string}` |

Example response:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "role": "warehouse_agent"
}
```

<a id="op-get-api-v1-auth-me"></a>
### `GET /api/v1/auth/me`

The signed-in user and role

**Access:** Any staff role · **Status:** Stub: returns 501

| Status | Meaning | Body |
| --- | --- | --- |
| 200 | Success | [`UserResponse`](#model-userresponse) |
| 401 | No or invalid bearer token | `{"detail": string}` |
| 403 | Signed in with another role | `{"detail": string}` |
| 501 | Planned, not implemented yet | `{"detail": string}` |

Example response:

```json
{
  "user_id": 1,
  "username": "warehouse1",
  "role": "warehouse_agent"
}
```

## Customer: orders

<a id="op-post-api-v1-orders-lookup"></a>
### `POST /api/v1/orders/lookup`

Find an order and explain which items can be returned

**Access:** Customer (no login) · **Status:** Stub: returns 501

**Request body:** [`OrderLookupRequest`](#model-orderlookuprequest)

```json
{
  "order_number": "ORD-104233",
  "email": "asha.verma@example.com"
}
```

| Status | Meaning | Body |
| --- | --- | --- |
| 200 | Success | [`OrderLookupResponse`](#model-orderlookupresponse) |
| 404 | No order matches this number and email | `{"detail": string}` |
| 422 | Validation Error | [`HTTPValidationError`](#model-httpvalidationerror) |
| 501 | Planned, not implemented yet | `{"detail": string}` |

Example response:

```json
{
  "order_number": "ORD-104233",
  "delivered_on": "2026-11-20",
  "items": [
    {
      "order_item_id": 1,
      "product_name": "Cotton kurta",
      "category": "Apparel",
      "unit_price": "1499.00",
      "quantity": 1,
      "eligible": true,
      "reason": "damaged",
      "window_ends_on": "2026-11-20"
    }
  ]
}
```

## Customer: returns

<a id="op-post-api-v1-returns"></a>
### `POST /api/v1/returns`

Request a return for one or more items

**Access:** Customer (no login) · **Status:** Stub: returns 501

**Request body:** [`CreateReturnRequest`](#model-createreturnrequest)

```json
{
  "order_number": "ORD-104233",
  "email": "asha.verma@example.com",
  "items": [
    {
      "order_item_id": 1,
      "quantity": 1
    }
  ],
  "reason": "damaged",
  "reason_details": "Seam torn on arrival",
  "refund_method": "original_payment"
}
```

| Status | Meaning | Body |
| --- | --- | --- |
| 201 | Success | [`ReturnDetailResponse`](#model-returndetailresponse) |
| 422 | An item is not eligible; the reason is in the message | `{"detail": string}` |
| 501 | Planned, not implemented yet | `{"detail": string}` |

Example response:

```json
{
  "return_code": "RR-7K2P9QX4",
  "status": "requested",
  "reason": "damaged",
  "refund_method": "original_payment",
  "items": [
    {
      "return_item_id": 1,
      "product_name": "Cotton kurta",
      "quantity": 1,
      "grade": null,
      "decision": null,
      "refund_amount": "1499.00"
    }
  ],
  "timeline": [
    {
      "status": "requested",
      "at": "2026-11-20T10:30:00Z",
      "note": "Parcel scanned at dock 2"
    }
  ],
  "refund_total": "2998.00",
  "created_at": "2026-11-20T10:30:00Z"
}
```

<a id="op-post-api-v1-returns-return-code-photo"></a>
### `POST /api/v1/returns/{return_code}/photo`

Upload a photo of the item (JPEG or PNG, stored locally)

**Access:** Customer (no login) · **Status:** Stub: returns 501

| Parameter | In | Type | Required | Rules |
| --- | --- | --- | --- | --- |
| `return_code` | path | string | yes | Return code on the QR label; min length 6, max length 32, pattern `^[A-Za-z0-9-]+$` |

**Request body:** `multipart/form-data` with `email` (string), `photo` (file)

| Status | Meaning | Body |
| --- | --- | --- |
| 201 | Success | [`PhotoUploadResponse`](#model-photouploadresponse) |
| 413 | File larger than UPLOAD_MAX_MB | `{"detail": string}` |
| 422 | Validation Error | [`HTTPValidationError`](#model-httpvalidationerror) |
| 501 | Planned, not implemented yet | `{"detail": string}` |

Example response:

```json
{
  "return_code": "RR-7K2P9QX4",
  "photo_url": "/uploads/RR-7K2P9QX4.jpg",
  "content_type": "image/jpeg",
  "size_bytes": 1
}
```

<a id="op-get-api-v1-returns-return-code"></a>
### `GET /api/v1/returns/{return_code}`

Return details

**Access:** Customer (no login) · **Status:** Stub: returns 501

| Parameter | In | Type | Required | Rules |
| --- | --- | --- | --- | --- |
| `return_code` | path | string | yes | Return code on the QR label; min length 6, max length 32, pattern `^[A-Za-z0-9-]+$` |
| `X-Customer-Email` | header | string | yes | max length 254, pattern `^[^@\s]+@[^@\s]+\.[^@\s]+$` |

| Status | Meaning | Body |
| --- | --- | --- |
| 200 | Success | [`ReturnDetailResponse`](#model-returndetailresponse) |
| 422 | Validation Error | [`HTTPValidationError`](#model-httpvalidationerror) |
| 501 | Planned, not implemented yet | `{"detail": string}` |

Example response:

```json
{
  "return_code": "RR-7K2P9QX4",
  "status": "requested",
  "reason": "damaged",
  "refund_method": "original_payment",
  "items": [
    {
      "return_item_id": 1,
      "product_name": "Cotton kurta",
      "quantity": 1,
      "grade": null,
      "decision": null,
      "refund_amount": "1499.00"
    }
  ],
  "timeline": [
    {
      "status": "requested",
      "at": "2026-11-20T10:30:00Z",
      "note": "Parcel scanned at dock 2"
    }
  ],
  "refund_total": "2998.00",
  "created_at": "2026-11-20T10:30:00Z"
}
```

<a id="op-get-api-v1-returns-return-code-timeline"></a>
### `GET /api/v1/returns/{return_code}/timeline`

Status timeline: Requested → … → Refunded or Rejected

**Access:** Customer (no login) · **Status:** Stub: returns 501

| Parameter | In | Type | Required | Rules |
| --- | --- | --- | --- | --- |
| `return_code` | path | string | yes | Return code on the QR label; min length 6, max length 32, pattern `^[A-Za-z0-9-]+$` |
| `X-Customer-Email` | header | string | yes | max length 254, pattern `^[^@\s]+@[^@\s]+\.[^@\s]+$` |

| Status | Meaning | Body |
| --- | --- | --- |
| 200 | Success | list[[`StatusEventResponse`](#model-statuseventresponse)] |
| 422 | Validation Error | [`HTTPValidationError`](#model-httpvalidationerror) |
| 501 | Planned, not implemented yet | `{"detail": string}` |

Example response:

```json
[
  {
    "status": "requested",
    "at": "2026-11-20T10:30:00Z",
    "note": "Parcel scanned at dock 2"
  }
]
```

<a id="op-get-api-v1-returns-return-code-label"></a>
### `GET /api/v1/returns/{return_code}/label`

Mock return label with a QR code

**Access:** Customer (no login) · **Status:** Stub: returns 501

| Parameter | In | Type | Required | Rules |
| --- | --- | --- | --- | --- |
| `return_code` | path | string | yes | Return code on the QR label; min length 6, max length 32, pattern `^[A-Za-z0-9-]+$` |
| `X-Customer-Email` | header | string | yes | max length 254, pattern `^[^@\s]+@[^@\s]+\.[^@\s]+$` |

| Status | Meaning | Body |
| --- | --- | --- |
| 200 | Success | [`ReturnLabelResponse`](#model-returnlabelresponse) |
| 422 | Validation Error | [`HTTPValidationError`](#model-httpvalidationerror) |
| 501 | Planned, not implemented yet | `{"detail": string}` |

Example response:

```json
{
  "return_code": "RR-7K2P9QX4",
  "qr_svg": "<svg ...>",
  "ship_to": "ReturnRight Warehouse, Indore 452010"
}
```

<a id="op-post-api-v1-returns-return-code-ship"></a>
### `POST /api/v1/returns/{return_code}/ship`

Customer confirms the parcel is shipped (Approved → In transit)

**Access:** Customer (no login) · **Status:** Stub: returns 501

| Parameter | In | Type | Required | Rules |
| --- | --- | --- | --- | --- |
| `return_code` | path | string | yes | Return code on the QR label; min length 6, max length 32, pattern `^[A-Za-z0-9-]+$` |

**Request body:** [`CustomerProofRequest`](#model-customerproofrequest)

```json
{
  "email": "asha.verma@example.com"
}
```

| Status | Meaning | Body |
| --- | --- | --- |
| 200 | Success | [`ReturnDetailResponse`](#model-returndetailresponse) |
| 409 | The return is not in the Approved state | `{"detail": string}` |
| 422 | Validation Error | [`HTTPValidationError`](#model-httpvalidationerror) |
| 501 | Planned, not implemented yet | `{"detail": string}` |

Example response:

```json
{
  "return_code": "RR-7K2P9QX4",
  "status": "requested",
  "reason": "damaged",
  "refund_method": "original_payment",
  "items": [
    {
      "return_item_id": 1,
      "product_name": "Cotton kurta",
      "quantity": 1,
      "grade": null,
      "decision": null,
      "refund_amount": "1499.00"
    }
  ],
  "timeline": [
    {
      "status": "requested",
      "at": "2026-11-20T10:30:00Z",
      "note": "Parcel scanned at dock 2"
    }
  ],
  "refund_total": "2998.00",
  "created_at": "2026-11-20T10:30:00Z"
}
```

## Warehouse

<a id="op-get-api-v1-warehouse-returns"></a>
### `GET /api/v1/warehouse/returns`

Work queue of returns, filtered by status

**Access:** Warehouse agent · **Status:** Stub: returns 501

| Parameter | In | Type | Required | Rules |
| --- | --- | --- | --- | --- |
| `status` | query | [`ReturnStatus`](#model-returnstatus) \| null | no | default `"in_transit"` |
| `page` | query | integer | no | ≥ 1, default `1` |
| `size` | query | integer | no | ≥ 1, ≤ 100, default `20` |

| Status | Meaning | Body |
| --- | --- | --- |
| 200 | Success | [`PageResponse_ReturnSummaryResponse_`](#model-pageresponse-returnsummaryresponse-) |
| 401 | No or invalid bearer token | `{"detail": string}` |
| 403 | Signed in with another role | `{"detail": string}` |
| 422 | Validation Error | [`HTTPValidationError`](#model-httpvalidationerror) |
| 501 | Planned, not implemented yet | `{"detail": string}` |

Example response:

```json
{
  "items": [
    {
      "return_code": "RR-7K2P9QX4",
      "status": "requested",
      "order_number": "ORD-104233",
      "item_count": 1,
      "refund_total": "2998.00",
      "customer_flagged": false,
      "created_at": "2026-11-20T10:30:00Z",
      "updated_at": "2026-11-20T10:30:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20
}
```

<a id="op-get-api-v1-warehouse-returns-return-code"></a>
### `GET /api/v1/warehouse/returns/{return_code}`

Find a return by its QR code

**Access:** Warehouse agent · **Status:** Stub: returns 501

| Parameter | In | Type | Required | Rules |
| --- | --- | --- | --- | --- |
| `return_code` | path | string | yes | Return code on the QR label; min length 6, max length 32, pattern `^[A-Za-z0-9-]+$` |

| Status | Meaning | Body |
| --- | --- | --- |
| 200 | Success | [`ReturnDetailResponse`](#model-returndetailresponse) |
| 401 | No or invalid bearer token | `{"detail": string}` |
| 403 | Signed in with another role | `{"detail": string}` |
| 422 | Validation Error | [`HTTPValidationError`](#model-httpvalidationerror) |
| 501 | Planned, not implemented yet | `{"detail": string}` |

Example response:

```json
{
  "return_code": "RR-7K2P9QX4",
  "status": "requested",
  "reason": "damaged",
  "refund_method": "original_payment",
  "items": [
    {
      "return_item_id": 1,
      "product_name": "Cotton kurta",
      "quantity": 1,
      "grade": null,
      "decision": null,
      "refund_amount": "1499.00"
    }
  ],
  "timeline": [
    {
      "status": "requested",
      "at": "2026-11-20T10:30:00Z",
      "note": "Parcel scanned at dock 2"
    }
  ],
  "refund_total": "2998.00",
  "created_at": "2026-11-20T10:30:00Z"
}
```

<a id="op-post-api-v1-warehouse-returns-return-code-receive"></a>
### `POST /api/v1/warehouse/returns/{return_code}/receive`

Mark the parcel received (In transit → Received)

**Access:** Warehouse agent · **Status:** Stub: returns 501

| Parameter | In | Type | Required | Rules |
| --- | --- | --- | --- | --- |
| `return_code` | path | string | yes | Return code on the QR label; min length 6, max length 32, pattern `^[A-Za-z0-9-]+$` |

| Status | Meaning | Body |
| --- | --- | --- |
| 200 | Success | [`ReturnDetailResponse`](#model-returndetailresponse) |
| 401 | No or invalid bearer token | `{"detail": string}` |
| 403 | Signed in with another role | `{"detail": string}` |
| 409 | The return is not In transit | `{"detail": string}` |
| 422 | Validation Error | [`HTTPValidationError`](#model-httpvalidationerror) |
| 501 | Planned, not implemented yet | `{"detail": string}` |

Example response:

```json
{
  "return_code": "RR-7K2P9QX4",
  "status": "requested",
  "reason": "damaged",
  "refund_method": "original_payment",
  "items": [
    {
      "return_item_id": 1,
      "product_name": "Cotton kurta",
      "quantity": 1,
      "grade": null,
      "decision": null,
      "refund_amount": "1499.00"
    }
  ],
  "timeline": [
    {
      "status": "requested",
      "at": "2026-11-20T10:30:00Z",
      "note": "Parcel scanned at dock 2"
    }
  ],
  "refund_total": "2998.00",
  "created_at": "2026-11-20T10:30:00Z"
}
```

<a id="op-post-api-v1-warehouse-returns-return-code-inspection"></a>
### `POST /api/v1/warehouse/returns/{return_code}/inspection`

Grade each item A, B or C and accept or reject it (Received → Inspected)

**Access:** Warehouse agent · **Status:** Stub: returns 501

| Parameter | In | Type | Required | Rules |
| --- | --- | --- | --- | --- |
| `return_code` | path | string | yes | Return code on the QR label; min length 6, max length 32, pattern `^[A-Za-z0-9-]+$` |

**Request body:** [`InspectionRequest`](#model-inspectionrequest)

```json
{
  "items": [
    {
      "return_item_id": 1,
      "grade": "A",
      "decision": "accept",
      "notes": "Tag attached, light wear"
    }
  ]
}
```

| Status | Meaning | Body |
| --- | --- | --- |
| 200 | Success | [`InspectionResultResponse`](#model-inspectionresultresponse) |
| 401 | No or invalid bearer token | `{"detail": string}` |
| 403 | Signed in with another role | `{"detail": string}` |
| 409 | The return is not Received | `{"detail": string}` |
| 422 | Validation Error | [`HTTPValidationError`](#model-httpvalidationerror) |
| 501 | Planned, not implemented yet | `{"detail": string}` |

Example response:

```json
{
  "return_code": "RR-7K2P9QX4",
  "status": "requested",
  "items": [
    {
      "return_item_id": 1,
      "product_name": "Cotton kurta",
      "quantity": 1,
      "grade": null,
      "decision": null,
      "refund_amount": "1499.00"
    }
  ],
  "refund_total": "2998.00",
  "needs_finance_approval": true
}
```

## Finance

<a id="op-get-api-v1-finance-approvals"></a>
### `GET /api/v1/finance/approvals`

Returns whose refund total is above the approval threshold

**Access:** Finance reviewer · **Status:** Stub: returns 501

| Parameter | In | Type | Required | Rules |
| --- | --- | --- | --- | --- |
| `page` | query | integer | no | ≥ 1, default `1` |
| `size` | query | integer | no | ≥ 1, ≤ 100, default `20` |

| Status | Meaning | Body |
| --- | --- | --- |
| 200 | Success | [`PageResponse_PendingApprovalResponse_`](#model-pageresponse-pendingapprovalresponse-) |
| 401 | No or invalid bearer token | `{"detail": string}` |
| 403 | Signed in with another role | `{"detail": string}` |
| 422 | Validation Error | [`HTTPValidationError`](#model-httpvalidationerror) |
| 501 | Planned, not implemented yet | `{"detail": string}` |

Example response:

```json
{
  "items": [
    {
      "return_code": "RR-7K2P9QX4",
      "customer_flagged": false,
      "refund_total": "2998.00",
      "refunds": [
        null
      ]
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20
}
```

<a id="op-post-api-v1-finance-approvals-return-code-decision"></a>
### `POST /api/v1/finance/approvals/{return_code}/decision`

Approve or reject a refund above the threshold

**Access:** Finance reviewer · **Status:** Stub: returns 501

| Parameter | In | Type | Required | Rules |
| --- | --- | --- | --- | --- |
| `return_code` | path | string | yes | Return code on the QR label; min length 6, max length 32, pattern `^[A-Za-z0-9-]+$` |

**Request body:** [`ApprovalDecisionRequest`](#model-approvaldecisionrequest)

```json
{
  "approve": true,
  "comment": "Photo matches the damage"
}
```

| Status | Meaning | Body |
| --- | --- | --- |
| 200 | Success | [`PendingApprovalResponse`](#model-pendingapprovalresponse) |
| 401 | No or invalid bearer token | `{"detail": string}` |
| 403 | Signed in with another role | `{"detail": string}` |
| 409 | Already decided | `{"detail": string}` |
| 422 | Validation Error | [`HTTPValidationError`](#model-httpvalidationerror) |
| 501 | Planned, not implemented yet | `{"detail": string}` |

Example response:

```json
{
  "return_code": "RR-7K2P9QX4",
  "customer_flagged": false,
  "refund_total": "2998.00",
  "refunds": [
    {
      "refund_id": 1,
      "return_code": "RR-7K2P9QX4",
      "return_item_id": 1,
      "amount": "1499.00",
      "method": "original_payment",
      "status": "pending_approval",
      "gateway_transaction_id": "gw_9f2c41",
      "approved_by": "finance1",
      "created_at": "2026-11-20T10:30:00Z"
    }
  ]
}
```

<a id="op-get-api-v1-finance-refunds"></a>
### `GET /api/v1/finance/refunds`

Refunds by status

**Access:** Finance reviewer · **Status:** Stub: returns 501

| Parameter | In | Type | Required | Rules |
| --- | --- | --- | --- | --- |
| `status` | query | [`RefundStatus`](#model-refundstatus) \| null | no |  |
| `page` | query | integer | no | ≥ 1, default `1` |
| `size` | query | integer | no | ≥ 1, ≤ 100, default `20` |

| Status | Meaning | Body |
| --- | --- | --- |
| 200 | Success | [`PageResponse_RefundResponse_`](#model-pageresponse-refundresponse-) |
| 401 | No or invalid bearer token | `{"detail": string}` |
| 403 | Signed in with another role | `{"detail": string}` |
| 422 | Validation Error | [`HTTPValidationError`](#model-httpvalidationerror) |
| 501 | Planned, not implemented yet | `{"detail": string}` |

Example response:

```json
{
  "items": [
    {
      "refund_id": 1,
      "return_code": "RR-7K2P9QX4",
      "return_item_id": 1,
      "amount": "1499.00",
      "method": "original_payment",
      "status": "pending_approval",
      "gateway_transaction_id": "gw_9f2c41",
      "approved_by": "finance1",
      "created_at": "2026-11-20T10:30:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20
}
```

<a id="op-get-api-v1-finance-refunds-refund-id"></a>
### `GET /api/v1/finance/refunds/{refund_id}`

One refund

**Access:** Finance reviewer · **Status:** Stub: returns 501

| Parameter | In | Type | Required | Rules |
| --- | --- | --- | --- | --- |
| `refund_id` | path | integer | yes | > 0 |

| Status | Meaning | Body |
| --- | --- | --- |
| 200 | Success | [`RefundResponse`](#model-refundresponse) |
| 401 | No or invalid bearer token | `{"detail": string}` |
| 403 | Signed in with another role | `{"detail": string}` |
| 422 | Validation Error | [`HTTPValidationError`](#model-httpvalidationerror) |
| 501 | Planned, not implemented yet | `{"detail": string}` |

Example response:

```json
{
  "refund_id": 1,
  "return_code": "RR-7K2P9QX4",
  "return_item_id": 1,
  "amount": "1499.00",
  "method": "original_payment",
  "status": "pending_approval",
  "gateway_transaction_id": "gw_9f2c41",
  "approved_by": "finance1",
  "created_at": "2026-11-20T10:30:00Z"
}
```

<a id="op-post-api-v1-finance-refunds-refund-id-pay"></a>
### `POST /api/v1/finance/refunds/{refund_id}/pay`

Pay an approved refund through the gateway (idempotent)

Send the same Idempotency-Key on every retry: a refund is never paid twice.

**Access:** Finance reviewer · **Status:** Stub: returns 501

| Parameter | In | Type | Required | Rules |
| --- | --- | --- | --- | --- |
| `refund_id` | path | integer | yes | > 0 |
| `Idempotency-Key` | header | string | yes | min length 8, max length 64 |

| Status | Meaning | Body |
| --- | --- | --- |
| 200 | Success | [`RefundResponse`](#model-refundresponse) |
| 401 | No or invalid bearer token | `{"detail": string}` |
| 403 | Signed in with another role | `{"detail": string}` |
| 409 | Not approved, or already paid with another key | `{"detail": string}` |
| 422 | Validation Error | [`HTTPValidationError`](#model-httpvalidationerror) |
| 501 | Planned, not implemented yet | `{"detail": string}` |

Example response:

```json
{
  "refund_id": 1,
  "return_code": "RR-7K2P9QX4",
  "return_item_id": 1,
  "amount": "1499.00",
  "method": "original_payment",
  "status": "pending_approval",
  "gateway_transaction_id": "gw_9f2c41",
  "approved_by": "finance1",
  "created_at": "2026-11-20T10:30:00Z"
}
```

<a id="op-get-api-v1-finance-ledger"></a>
### `GET /api/v1/finance/ledger`

Ledger of gateway refunds and store credit

**Access:** Finance reviewer · **Status:** Stub: returns 501

| Parameter | In | Type | Required | Rules |
| --- | --- | --- | --- | --- |
| `refund_id` | query | integer \| null | no | > 0 |
| `page` | query | integer | no | ≥ 1, default `1` |
| `size` | query | integer | no | ≥ 1, ≤ 100, default `20` |

| Status | Meaning | Body |
| --- | --- | --- |
| 200 | Success | [`PageResponse_LedgerEntryResponse_`](#model-pageresponse-ledgerentryresponse-) |
| 401 | No or invalid bearer token | `{"detail": string}` |
| 403 | Signed in with another role | `{"detail": string}` |
| 422 | Validation Error | [`HTTPValidationError`](#model-httpvalidationerror) |
| 501 | Planned, not implemented yet | `{"detail": string}` |

Example response:

```json
{
  "items": [
    {
      "entry_id": 1,
      "refund_id": 1,
      "entry_type": "gateway_refund",
      "amount": "1499.00",
      "created_at": "2026-11-20T10:30:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20
}
```

## Dashboard

<a id="op-get-api-v1-dashboard"></a>
### `GET /api/v1/dashboard`

All dashboard metrics in one call

**Access:** Operations manager · **Status:** Stub: returns 501

| Parameter | In | Type | Required | Rules |
| --- | --- | --- | --- | --- |
| `date_from` | query | date \| null | no | Inclusive start date |
| `date_to` | query | date \| null | no | Inclusive end date |

| Status | Meaning | Body |
| --- | --- | --- |
| 200 | Success | [`DashboardResponse`](#model-dashboardresponse) |
| 401 | No or invalid bearer token | `{"detail": string}` |
| 403 | Signed in with another role | `{"detail": string}` |
| 422 | Validation Error | [`HTTPValidationError`](#model-httpvalidationerror) |
| 501 | Planned, not implemented yet | `{"detail": string}` |

Example response:

```json
{
  "return_rate_by_category": [
    {
      "category": "Apparel",
      "orders": 1,
      "returns": 1,
      "return_rate": 0.12
    }
  ],
  "top_reasons": [
    {
      "reason": "damaged",
      "count": 1
    }
  ],
  "average_cycle_time_hours": 36.5,
  "flagged_customers": [
    {
      "customer_id": 1,
      "name": "Asha Verma",
      "returns_last_30_days": 1
    }
  ],
  "generated_at": "2026-11-20T10:30:00Z"
}
```

<a id="op-get-api-v1-dashboard-return-rates"></a>
### `GET /api/v1/dashboard/return-rates`

Return rate by category

**Access:** Operations manager · **Status:** Stub: returns 501

| Parameter | In | Type | Required | Rules |
| --- | --- | --- | --- | --- |
| `date_from` | query | date \| null | no | Inclusive start date |
| `date_to` | query | date \| null | no | Inclusive end date |

| Status | Meaning | Body |
| --- | --- | --- |
| 200 | Success | list[[`CategoryReturnRateResponse`](#model-categoryreturnrateresponse)] |
| 401 | No or invalid bearer token | `{"detail": string}` |
| 403 | Signed in with another role | `{"detail": string}` |
| 422 | Validation Error | [`HTTPValidationError`](#model-httpvalidationerror) |
| 501 | Planned, not implemented yet | `{"detail": string}` |

Example response:

```json
[
  {
    "category": "Apparel",
    "orders": 1,
    "returns": 1,
    "return_rate": 0.12
  }
]
```

<a id="op-get-api-v1-dashboard-top-reasons"></a>
### `GET /api/v1/dashboard/top-reasons`

Top return reasons

**Access:** Operations manager · **Status:** Stub: returns 501

| Parameter | In | Type | Required | Rules |
| --- | --- | --- | --- | --- |
| `date_from` | query | date \| null | no | Inclusive start date |
| `date_to` | query | date \| null | no | Inclusive end date |
| `limit` | query | integer | no | ≥ 1, ≤ 20, default `5` |

| Status | Meaning | Body |
| --- | --- | --- |
| 200 | Success | list[[`ReasonCountResponse`](#model-reasoncountresponse)] |
| 401 | No or invalid bearer token | `{"detail": string}` |
| 403 | Signed in with another role | `{"detail": string}` |
| 422 | Validation Error | [`HTTPValidationError`](#model-httpvalidationerror) |
| 501 | Planned, not implemented yet | `{"detail": string}` |

Example response:

```json
[
  {
    "reason": "damaged",
    "count": 1
  }
]
```

<a id="op-get-api-v1-dashboard-flagged-customers"></a>
### `GET /api/v1/dashboard/flagged-customers`

Customers with more than 3 returns in 30 days

**Access:** Operations manager · **Status:** Stub: returns 501

| Status | Meaning | Body |
| --- | --- | --- |
| 200 | Success | list[[`FlaggedCustomerResponse`](#model-flaggedcustomerresponse)] |
| 401 | No or invalid bearer token | `{"detail": string}` |
| 403 | Signed in with another role | `{"detail": string}` |
| 501 | Planned, not implemented yet | `{"detail": string}` |

Example response:

```json
[
  {
    "customer_id": 1,
    "name": "Asha Verma",
    "returns_last_30_days": 1
  }
]
```

## Audit

<a id="op-get-api-v1-audit"></a>
### `GET /api/v1/audit`

Audit log, newest first

**Access:** Operations manager · **Status:** Stub: returns 501

| Parameter | In | Type | Required | Rules |
| --- | --- | --- | --- | --- |
| `entity` | query | string \| null | no | max length 50 |
| `entity_id` | query | integer \| null | no | > 0 |
| `page` | query | integer | no | ≥ 1, default `1` |
| `size` | query | integer | no | ≥ 1, ≤ 100, default `20` |

| Status | Meaning | Body |
| --- | --- | --- |
| 200 | Success | [`PageResponse_AuditLogResponse_`](#model-pageresponse-auditlogresponse-) |
| 401 | No or invalid bearer token | `{"detail": string}` |
| 403 | Signed in with another role | `{"detail": string}` |
| 422 | Validation Error | [`HTTPValidationError`](#model-httpvalidationerror) |
| 501 | Planned, not implemented yet | `{"detail": string}` |

Example response:

```json
{
  "items": [
    {
      "audit_id": 1,
      "entity": "return_request",
      "entity_id": 1,
      "from_status": "in_transit",
      "to_status": "received",
      "actor": "warehouse1",
      "actor_role": null,
      "reason": "damaged",
      "created_at": "2026-11-20T10:30:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20
}
```

<a id="op-get-api-v1-audit-returns-return-code"></a>
### `GET /api/v1/audit/returns/{return_code}`

Every state change of one return, oldest first

**Access:** Operations manager · **Status:** Stub: returns 501

| Parameter | In | Type | Required | Rules |
| --- | --- | --- | --- | --- |
| `return_code` | path | string | yes | Return code on the QR label; min length 6, max length 32, pattern `^[A-Za-z0-9-]+$` |

| Status | Meaning | Body |
| --- | --- | --- |
| 200 | Success | list[[`AuditLogResponse`](#model-auditlogresponse)] |
| 401 | No or invalid bearer token | `{"detail": string}` |
| 403 | Signed in with another role | `{"detail": string}` |
| 422 | Validation Error | [`HTTPValidationError`](#model-httpvalidationerror) |
| 501 | Planned, not implemented yet | `{"detail": string}` |

Example response:

```json
[
  {
    "audit_id": 1,
    "entity": "return_request",
    "entity_id": 1,
    "from_status": "in_transit",
    "to_status": "received",
    "actor": "warehouse1",
    "actor_role": "warehouse_agent",
    "reason": "damaged",
    "created_at": "2026-11-20T10:30:00Z"
  }
]
```

## Enums

| Enum | Values |
| --- | --- |
| <a id="model-grade"></a>`Grade` | `A`, `B`, `C` |
| <a id="model-itemdecision"></a>`ItemDecision` | `accept`, `reject` |
| <a id="model-ledgerentrytype"></a>`LedgerEntryType` | `gateway_refund`, `store_credit` |
| <a id="model-refundmethod"></a>`RefundMethod` | `original_payment`, `store_credit` |
| <a id="model-refundstatus"></a>`RefundStatus` | `pending_approval`, `approved`, `paid`, `failed`, `rejected` |
| <a id="model-returnreason"></a>`ReturnReason` | `damaged`, `wrong_item`, `not_as_described`, `size_or_fit`, `no_longer_needed`, `other` |
| <a id="model-returnstatus"></a>`ReturnStatus` | `requested`, `approved`, `in_transit`, `received`, `inspected`, `refunded`, `rejected` |
| <a id="model-role"></a>`Role` | `warehouse_agent`, `finance_reviewer`, `operations_manager` |

## Models

<a id="model-approvaldecisionrequest"></a>
### `ApprovalDecisionRequest`

Unknown fields are rejected.

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `approve` | boolean | yes |  |
| `comment` | string \| null | no | max length 500 |

<a id="model-auditlogresponse"></a>
### `AuditLogResponse`

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `audit_id` | integer | yes |  |
| `entity` | string | yes |  |
| `entity_id` | integer | yes |  |
| `from_status` | string \| null | yes |  |
| `to_status` | string | yes |  |
| `actor` | string | yes |  |
| `actor_role` | [`Role`](#model-role) \| null | yes |  |
| `reason` | string \| null | no |  |
| `created_at` | datetime | yes |  |

<a id="model-categoryreturnrateresponse"></a>
### `CategoryReturnRateResponse`

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `category` | string | yes |  |
| `orders` | integer | yes |  |
| `returns` | integer | yes |  |
| `return_rate` | number | yes |  |

<a id="model-createreturnrequest"></a>
### `CreateReturnRequest`

Unknown fields are rejected.

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `order_number` | string | yes | pattern `^[A-Za-z0-9-]{4,32}$` |
| `email` | string | yes | max length 254, pattern `^[^@\s]+@[^@\s]+\.[^@\s]+$` |
| `items` | list[[`ReturnItemRequest`](#model-returnitemrequest)] | yes | min items 1, max items 20 |
| `reason` | [`ReturnReason`](#model-returnreason) | yes |  |
| `reason_details` | string \| null | no | max length 500 |
| `refund_method` | [`RefundMethod`](#model-refundmethod) | yes |  |

<a id="model-customerproofrequest"></a>
### `CustomerProofRequest`

Sent with customer actions on an existing return, such as marking it shipped.

Unknown fields are rejected.

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `email` | string | yes | max length 254, pattern `^[^@\s]+@[^@\s]+\.[^@\s]+$` |

<a id="model-dashboardresponse"></a>
### `DashboardResponse`

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `return_rate_by_category` | list[[`CategoryReturnRateResponse`](#model-categoryreturnrateresponse)] | yes |  |
| `top_reasons` | list[[`ReasonCountResponse`](#model-reasoncountresponse)] | yes |  |
| `average_cycle_time_hours` | number \| null | yes |  |
| `flagged_customers` | list[[`FlaggedCustomerResponse`](#model-flaggedcustomerresponse)] | yes |  |
| `generated_at` | datetime | yes |  |

<a id="model-flaggedcustomerresponse"></a>
### `FlaggedCustomerResponse`

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `customer_id` | integer | yes |  |
| `name` | string | yes |  |
| `returns_last_30_days` | integer | yes |  |

<a id="model-httpvalidationerror"></a>
### `HTTPValidationError`

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `detail` | list[[`ValidationError`](#model-validationerror)] | no |  |

<a id="model-healthresponse"></a>
### `HealthResponse`

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `status` | `"ok"` \| `"degraded"` \| `"down"` | yes |  |
| `database` | `"ok"` \| `"degraded"` \| `"down"` | yes |  |
| `gateway` | `"ok"` \| `"degraded"` \| `"down"` | yes |  |

<a id="model-inspectionrequest"></a>
### `InspectionRequest`

Unknown fields are rejected.

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `items` | list[[`ItemInspectionRequest`](#model-iteminspectionrequest)] | yes | min items 1, max items 20 |

<a id="model-inspectionresultresponse"></a>
### `InspectionResultResponse`

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `return_code` | string | yes |  |
| `status` | [`ReturnStatus`](#model-returnstatus) | yes |  |
| `items` | list[[`ReturnItemResponse`](#model-returnitemresponse)] | yes |  |
| `refund_total` | decimal (string) | yes |  |
| `needs_finance_approval` | boolean | yes |  |

<a id="model-itemeligibilityresponse"></a>
### `ItemEligibilityResponse`

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `order_item_id` | integer | yes |  |
| `product_name` | string | yes |  |
| `category` | string | yes |  |
| `unit_price` | decimal (string) | yes |  |
| `quantity` | integer | yes |  |
| `eligible` | boolean | yes |  |
| `reason` | string | yes |  |
| `window_ends_on` | date \| null | no |  |

<a id="model-iteminspectionrequest"></a>
### `ItemInspectionRequest`

Unknown fields are rejected.

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `return_item_id` | integer | yes | > 0.0 |
| `grade` | [`Grade`](#model-grade) | yes |  |
| `decision` | [`ItemDecision`](#model-itemdecision) | yes |  |
| `notes` | string \| null | no | max length 500 |

<a id="model-ledgerentryresponse"></a>
### `LedgerEntryResponse`

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `entry_id` | integer | yes |  |
| `refund_id` | integer | yes |  |
| `entry_type` | [`LedgerEntryType`](#model-ledgerentrytype) | yes |  |
| `amount` | decimal (string) | yes |  |
| `created_at` | datetime | yes |  |

<a id="model-livenessresponse"></a>
### `LivenessResponse`

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `status` | `"ok"` | no | default `"ok"` |

<a id="model-loginrequest"></a>
### `LoginRequest`

Unknown fields are rejected.

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `username` | string | yes | min length 3, max length 50 |
| `password` | string | yes | min length 6, max length 128 |

<a id="model-orderlookuprequest"></a>
### `OrderLookupRequest`

Unknown fields are rejected.

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `order_number` | string | yes | pattern `^[A-Za-z0-9-]{4,32}$` |
| `email` | string | yes | max length 254, pattern `^[^@\s]+@[^@\s]+\.[^@\s]+$` |

<a id="model-orderlookupresponse"></a>
### `OrderLookupResponse`

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `order_number` | string | yes |  |
| `delivered_on` | date \| null | yes |  |
| `items` | list[[`ItemEligibilityResponse`](#model-itemeligibilityresponse)] | yes |  |

<a id="model-pageresponse-auditlogresponse-"></a>
### `PageResponse_AuditLogResponse_`

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `items` | list[[`AuditLogResponse`](#model-auditlogresponse)] | yes |  |
| `total` | integer | yes |  |
| `page` | integer | yes |  |
| `size` | integer | yes |  |

<a id="model-pageresponse-ledgerentryresponse-"></a>
### `PageResponse_LedgerEntryResponse_`

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `items` | list[[`LedgerEntryResponse`](#model-ledgerentryresponse)] | yes |  |
| `total` | integer | yes |  |
| `page` | integer | yes |  |
| `size` | integer | yes |  |

<a id="model-pageresponse-pendingapprovalresponse-"></a>
### `PageResponse_PendingApprovalResponse_`

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `items` | list[[`PendingApprovalResponse`](#model-pendingapprovalresponse)] | yes |  |
| `total` | integer | yes |  |
| `page` | integer | yes |  |
| `size` | integer | yes |  |

<a id="model-pageresponse-refundresponse-"></a>
### `PageResponse_RefundResponse_`

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `items` | list[[`RefundResponse`](#model-refundresponse)] | yes |  |
| `total` | integer | yes |  |
| `page` | integer | yes |  |
| `size` | integer | yes |  |

<a id="model-pageresponse-returnsummaryresponse-"></a>
### `PageResponse_ReturnSummaryResponse_`

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `items` | list[[`ReturnSummaryResponse`](#model-returnsummaryresponse)] | yes |  |
| `total` | integer | yes |  |
| `page` | integer | yes |  |
| `size` | integer | yes |  |

<a id="model-pendingapprovalresponse"></a>
### `PendingApprovalResponse`

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `return_code` | string | yes |  |
| `customer_flagged` | boolean | yes |  |
| `refund_total` | decimal (string) | yes |  |
| `refunds` | list[[`RefundResponse`](#model-refundresponse)] | yes |  |

<a id="model-photouploadresponse"></a>
### `PhotoUploadResponse`

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `return_code` | string | yes |  |
| `photo_url` | string | yes |  |
| `content_type` | string | yes |  |
| `size_bytes` | integer | yes |  |

<a id="model-reasoncountresponse"></a>
### `ReasonCountResponse`

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `reason` | [`ReturnReason`](#model-returnreason) | yes |  |
| `count` | integer | yes |  |

<a id="model-refundresponse"></a>
### `RefundResponse`

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `refund_id` | integer | yes |  |
| `return_code` | string | yes |  |
| `return_item_id` | integer | yes |  |
| `amount` | decimal (string) | yes |  |
| `method` | [`RefundMethod`](#model-refundmethod) | yes |  |
| `status` | [`RefundStatus`](#model-refundstatus) | yes |  |
| `gateway_transaction_id` | string \| null | no |  |
| `approved_by` | string \| null | no |  |
| `created_at` | datetime | yes |  |

<a id="model-returndetailresponse"></a>
### `ReturnDetailResponse`

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `return_code` | string | yes |  |
| `status` | [`ReturnStatus`](#model-returnstatus) | yes |  |
| `reason` | [`ReturnReason`](#model-returnreason) | yes |  |
| `refund_method` | [`RefundMethod`](#model-refundmethod) | yes |  |
| `items` | list[[`ReturnItemResponse`](#model-returnitemresponse)] | yes |  |
| `timeline` | list[[`StatusEventResponse`](#model-statuseventresponse)] | yes |  |
| `refund_total` | decimal (string) \| null | no |  |
| `created_at` | datetime | yes |  |

<a id="model-returnitemrequest"></a>
### `ReturnItemRequest`

Unknown fields are rejected.

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `order_item_id` | integer | yes | > 0.0 |
| `quantity` | integer | no | ≥ 1.0, ≤ 10.0, default `1` |

<a id="model-returnitemresponse"></a>
### `ReturnItemResponse`

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `return_item_id` | integer | yes |  |
| `product_name` | string | yes |  |
| `quantity` | integer | yes |  |
| `grade` | [`Grade`](#model-grade) \| null | no |  |
| `decision` | [`ItemDecision`](#model-itemdecision) \| null | no |  |
| `refund_amount` | decimal (string) \| null | no |  |

<a id="model-returnlabelresponse"></a>
### `ReturnLabelResponse`

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `return_code` | string | yes |  |
| `qr_svg` | string | yes |  |
| `ship_to` | string | yes |  |

<a id="model-returnsummaryresponse"></a>
### `ReturnSummaryResponse`

One row in a staff work queue.

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `return_code` | string | yes |  |
| `status` | [`ReturnStatus`](#model-returnstatus) | yes |  |
| `order_number` | string | yes |  |
| `item_count` | integer | yes |  |
| `refund_total` | decimal (string) \| null | no |  |
| `customer_flagged` | boolean | no | default `false` |
| `created_at` | datetime | yes |  |
| `updated_at` | datetime | yes |  |

<a id="model-statuseventresponse"></a>
### `StatusEventResponse`

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `status` | [`ReturnStatus`](#model-returnstatus) | yes |  |
| `at` | datetime | yes |  |
| `note` | string \| null | no |  |

<a id="model-tokenresponse"></a>
### `TokenResponse`

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `access_token` | string | yes |  |
| `token_type` | `"bearer"` | no | default `"bearer"` |
| `expires_in` | integer | yes |  |
| `role` | [`Role`](#model-role) | yes |  |

<a id="model-userresponse"></a>
### `UserResponse`

The signed-in internal user.

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `user_id` | integer | yes |  |
| `username` | string | yes |  |
| `role` | [`Role`](#model-role) | yes |  |

<a id="model-validationerror"></a>
### `ValidationError`

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `loc` | list[string \| integer] | yes |  |
| `msg` | string | yes |  |
| `type` | string | yes |  |
| `input` | any | no |  |
| `ctx` | object | no |  |
