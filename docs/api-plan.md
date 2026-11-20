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
| Lists | `?page=1&size=20` → `PageResponse` (`items`, `total`, `page`, `size`) |
| Errors | `ErrorResponse` (`code`, `message`, `request_id`); 409 invalid state transition, 422 not eligible or bad input |
| Stubs | Validate input, check the role, then `501` naming the planned feature |

## Endpoints

| # | Method | Path | Who | Request | Response | Must-have |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | GET | `/health` | Anyone | - | `LivenessResponse` | Ops |
| 2 | GET | `/health/ready` | Anyone | - | `HealthResponse` (database, gateway) | Ops |
| 3 | POST | `/auth/login` | Internal staff | `LoginRequest` | `TokenResponse` | 4, 5, 6 |
| 4 | GET | `/auth/me` | Any internal role | - | `UserResponse` | 4, 5, 6 |
| 5 | POST | `/orders/lookup` | Customer | `OrderLookupRequest` | `OrderLookupResponse` (eligibility + reason per item) | 1, 2 |
| 6 | POST | `/returns` | Customer | `CreateReturnRequest` | `ReturnDetailResponse` (201) | 1, 2, 7 |
| 7 | POST | `/returns/{return_code}/photo` | Customer | multipart: `email`, `photo` | `PhotoUploadResponse` | 1 |
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
| Requested | Approved or Rejected | inside `POST /returns`, after the eligibility engine runs | System |
| Approved | In transit | `POST /returns/{code}/ship` | Customer |
| In transit | Received | `POST /warehouse/returns/{code}/receive` | Warehouse agent |
| Received | Inspected or Rejected | `POST /warehouse/returns/{code}/inspection` | Warehouse agent |
| Inspected | Refunded | refund paid automatically (≤ 10,000 INR), or after `POST /finance/approvals/{code}/decision` | System, finance reviewer |

Every row writes one audit log entry in the same transaction.

## Open questions

- [ ] Is a return auto-approved when every item is eligible? The plan above assumes yes.
- [ ] Does `/finance/refunds/{id}/pay` stay as a manual retry, or do refunds only pay automatically?
- [ ] Do warehouse agents need a list endpoint, or is scanning enough?
