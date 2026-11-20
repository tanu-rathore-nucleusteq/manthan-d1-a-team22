# ReturnRight API Plan

The API has 27 endpoints under `/api/v1` that cover the seven must-haves. All of them exist as typed stubs. Each one validates its request and returns `501 Not Implemented` until its story is built. Health checks and the PostgreSQL connection are implemented now.

The frontend builds against `/openapi.json`. The request and response shapes live in `src/api/returnright/dtos/`.

## Conventions

| Topic | Decision |
| --- | --- |
| Prefix | `/api/v1`; Prometheus `/metrics` stays outside it |
| Customer identity | No login. The order number plus email proves ownership (lookup, create). Later calls on a return send the email in the `X-Customer-Email` header, or in the body for actions. Return codes are unguessable |
| Internal identity | `POST /auth/login` issues a JWT with a role claim. Protected routes use `require_role(...)` and return 401 when no token is sent |
| Refund idempotency | `Idempotency-Key` header on pay calls. The database is also unique per return item (ADR-001) |
| Failed refunds | A gateway error sets the refund to `failed`; `POST /finance/refunds/{refund_id}/pay` retries it with the same key |
| Store credit | Recorded in the ledger only; never sent to the gateway |
| Reasons and photos | Recorded per returned item, as in `db/schema_v2.sql` |
| Enum values | Lowercase in the API (`in_transit`); the database stores the upper-case member names (`IN_TRANSIT`) |
| Lists | `?page=1&size=20` → `PageResponse` (`items`, `total`, `page`, `size`) |
| Errors | `ErrorResponse` (`code`, `message`, `request_id`); 409 invalid state transition or duplicate return, 422 not eligible or bad input |
| Stubs | Validate input, check the role, then `501` naming the planned feature |

## Endpoints

| # | Method | Path | Who | Request | Response | Must-have |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | GET | `/health` | Anyone | - | `LivenessResponse` | Ops |
| 2 | GET | `/health/ready` | Anyone | - | `HealthResponse` (database, gateway) | Ops |
| 3 | POST | `/auth/login` | Internal staff | `LoginRequest` | `TokenResponse` | 4, 5, 6 |
| 4 | GET | `/auth/me` | Any internal role | - | `UserResponse` | 4, 5, 6 |
| 5 | POST | `/orders/lookup` | Customer | `OrderLookupRequest` | `OrderLookupResponse` (eligibility + reason per item) | 1, 2 |
| 6 | POST | `/returns` | Customer | `CreateReturnRequest` (reason per item) | `ReturnDetailResponse` (201) | 1, 2, 7 |
| 7 | POST | `/returns/{return_code}/photo` | Customer | multipart: `email`, `return_item_id`, `photo` | `PhotoUploadResponse` | 1 |
| 8 | GET | `/returns/{return_code}` | Customer | header `X-Customer-Email` | `ReturnDetailResponse` | 3 |
| 9 | GET | `/returns/{return_code}/timeline` | Customer | header `X-Customer-Email` | `list[StatusEventResponse]` | 3 |
| 10 | GET | `/returns/{return_code}/label` | Customer | header `X-Customer-Email` | `ReturnLabelResponse` (QR code) | 3 |
| 11 | POST | `/returns/{return_code}/ship` | Customer | `CustomerProofRequest` | `ReturnDetailResponse` (Approved → In transit) | 3, 7 |
| 12 | GET | `/warehouse/returns` | Warehouse agent | `?status=in_transit&page&size` | `PageResponse[ReturnSummaryResponse]` | 4 |
| 13 | GET | `/warehouse/returns/{return_code}` | Warehouse agent | QR code value | `ReturnDetailResponse` | 4 |
| 14 | POST | `/warehouse/returns/{return_code}/receive` | Warehouse agent | - | `ReturnDetailResponse` (In transit → Received) | 4, 7 |
| 15 | POST | `/warehouse/returns/{return_code}/inspection` | Warehouse agent | `InspectionRequest` (grade + decision per item) | `InspectionResultResponse` | 4, 7 |
| 16 | GET | `/finance/approvals` | Finance reviewer | `?page&size` | `PageResponse[PendingApprovalResponse]` | 5 |
| 17 | POST | `/finance/approvals/{return_code}/decision` | Finance reviewer | `ApprovalDecisionRequest` | `PendingApprovalResponse` | 5, 7 |
| 18 | GET | `/finance/refunds` | Finance reviewer | `?status&page&size` | `PageResponse[RefundResponse]` | 5 |
| 19 | GET | `/finance/refunds/{refund_id}` | Finance reviewer | - | `RefundResponse` | 5 |
| 20 | POST | `/finance/refunds/{refund_id}/pay` | Finance reviewer | header `Idempotency-Key` | `RefundResponse` | 5, 7 |
| 21 | GET | `/finance/ledger` | Finance reviewer | `?refund_id&page&size` | `PageResponse[LedgerEntryResponse]` | 5 |
| 22 | GET | `/dashboard` | Operations manager | `?date_from&date_to` | `DashboardResponse` | 6 |
| 23 | GET | `/dashboard/return-rates` | Operations manager | `?date_from&date_to` | `list[CategoryReturnRateResponse]` | 6 |
| 24 | GET | `/dashboard/top-reasons` | Operations manager | `?date_from&date_to&limit` | `list[ReasonCountResponse]` | 6 |
| 25 | GET | `/dashboard/flagged-customers` | Operations manager | - | `list[FlaggedCustomerResponse]` | 6 |
| 26 | GET | `/audit` | Operations manager | `?entity&entity_id&page&size` | `PageResponse[AuditLogResponse]` | 7 |
| 27 | GET | `/audit/returns/{return_code}` | Operations manager | - | `list[AuditLogResponse]` | 7 |

## State changes by endpoint

| From | To | Endpoint | Actor |
| --- | --- | --- | --- |
| - | Requested | `POST /returns` | Customer |
| Requested | Approved | inside `POST /returns`, once every submitted item is confirmed eligible; an ineligible item answers 422 and nothing is saved | System |
| Approved | In transit | `POST /returns/{code}/ship` | Customer |
| In transit | Received | `POST /warehouse/returns/{code}/receive` | Warehouse agent |
| Received | Inspected, or Rejected when every item is rejected | `POST /warehouse/returns/{code}/inspection` | Warehouse agent |
| Inspected | Refunded | refund paid automatically (return total ≤ 10,000 INR), or after an approval through `POST /finance/approvals/{code}/decision` | System, finance reviewer |
| Inspected | Rejected | a rejection through `POST /finance/approvals/{code}/decision` | Finance reviewer |

Every row writes one audit log entry in the same transaction.

## Decisions

- [x] A return is auto-approved when every submitted item is eligible. The wizard only offers eligible items and shows the reason for the others; the API answers 422 if an ineligible item is sent.
- [x] Refunds pay automatically: after inspection when the return total is 10,000 INR or less, after approval when it is more. `/finance/refunds/{id}/pay` stays as the retry for failed or timed-out refunds.
- [x] Warehouse agents keep the list endpoint as their work queue; scanning or typing the code opens one return.
