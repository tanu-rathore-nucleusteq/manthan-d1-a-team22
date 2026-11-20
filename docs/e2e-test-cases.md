# End-to-End Test Cases

Every implemented flow has a written case and an automated test: 34 cases, all passing on 2026-11-20. The first ten are the build plan's required end-to-end cases. Cases 11 to 34 cover the failure modes from the state-machine review and the remaining business rules.

API cases run through the real FastAPI app against PostgreSQL. Each test runs inside a transaction that is rolled back, so it leaves no data behind. Unless a case says otherwise, every automated test named below is in `tests/api/integration/test_return_flow.py`. Cases marked **UI** are also covered in the browser by Playwright (`tests/e2e/specs/`).

## How to run

```powershell
docker compose up -d db                                   # PostgreSQL on localhost:5434
pytest -q tests/api/integration/test_return_flow.py       # API end-to-end cases (skipped if the database is down)
pytest -q                                                 # everything: unit, integration, gateway
cd tests/e2e; npm install; npx playwright test             # UI cases (starts the web app; needs API and gateway running)
```

## The build plan's 10 end-to-end cases

| ID | Case | Steps | Expected result | Automated test |
| --- | --- | --- | --- | --- |
| E2E-01 | Shirt returned on day 5, grade A, 1,500 INR | Order delivered 5 days ago → create return → ship → receive → inspect grade A, accept | Status `refunded`, refund 1,500.00, gateway called once, exactly 1 ledger row | `test_grade_a_return_is_refunded_once_with_one_ledger_row` · **UI** `customer-return.spec.ts` |
| E2E-02 | Electronics returned on day 11 | Electronics order delivered 11 days ago → create return | 422 `item_not_eligible`; reason names the 10-day window | `test_electronics_on_day_11_are_refused_with_422_and_the_reason` · **UI** `customer-return.spec.ts` |
| E2E-03 | Innerwear item selected | Innerwear order → create return | 422 `item_not_eligible`; reason says the item can't be returned | `test_innerwear_item_is_refused_with_422_when_submitted`; lookup: `test_order_repository.py::test_innerwear_and_perishables_refused_end_to_end` |
| E2E-04 | Item returned on day 30 and day 31 | Apparel orders delivered 30 and 31 days ago → create return | Day 30: 201 created. Day 31: 422, "30-day return window ended" | `test_return_window_boundary_on_submit` (both days); lookup: `test_order_repository.py::test_lookup_on_day_30_is_returnable_end_to_end` |
| E2E-05 | Grade C item, 2,000 INR | Return received → inspect grade C, accept | Refund 1,000.00 (50%), status `refunded` | `test_grade_c_item_of_2000_refunds_1000` · **UI** `staff.spec.ts` |
| E2E-06 | Refund of 12,000 INR | Two 6,000 items → inspect grade A | Status `inspected`, `needs_finance_approval` true, appears in the finance queue, gateway not called; paid only after approval | `test_two_items_of_6000_wait_for_finance_and_pay_only_after_approval` · **UI** `staff.spec.ts` |
| E2E-07 | Mixed basket: one eligible item, one not | Electronics (day 14) + apparel (day 14) → submit both, then apparel alone | Both: 422 naming only the electronics item and its 10-day reason. Apparel alone: 201 with 1 item | `test_mixed_basket_is_refused_with_the_reason_and_the_eligible_item_alone_succeeds` |
| E2E-08 | Refund clicked twice / gateway retry | (a) Gateway fails once, then retry pay twice with one key. (b) Pay an already paid refund twice | Paid once: 1 successful gateway payment, 1 ledger row, status `paid` both times | `test_failed_gateway_payment_is_retried_with_the_same_key_and_pays_once`, `test_double_click_on_pay_for_a_paid_refund_pays_once`; gateway: `tests/gateway/test_payments.py::test_same_key_pays_once_and_replays_the_first_answer` |
| E2E-09 | Customer makes a 4th return in 30 days | Same customer creates 4 returns | Not flagged after the 3rd; flagged after the 4th; exactly 1 flag row | `test_fourth_return_in_30_days_flags_the_customer_and_the_third_does_not` |
| E2E-10 | Label scanned twice | Receive a return, then receive it again | Second scan: 409 `already_received`, no change | `test_scanning_a_parcel_twice_answers_already_received` |

## Failure modes and remaining rules

| ID | Case | Expected result | Automated test |
| --- | --- | --- | --- |
| E2E-11 | Grade B item, 2,000 INR | Refund 2,000.00 (100%) | `test_grade_b_item_refunds_the_full_price` |
| E2E-12 | Refund total exactly 10,000.00 | Paid without finance (threshold is strictly above 10,000) | `test_refund_of_exactly_10000_is_paid_without_finance` |
| E2E-13 | Refund total 10,000.01 | Waits for finance, gateway not called | `test_refund_of_10000_01_waits_for_finance` |
| E2E-14 | Finance rejects a refund | Refund `rejected`, return `rejected`, gateway not called | `test_finance_rejection_closes_the_return_without_paying` |
| E2E-15 | Finance approves twice | Second decision: 409 `already_decided`; paid once | `test_two_items_of_6000_wait_for_finance_and_pay_only_after_approval` · **UI** `staff.spec.ts` |
| E2E-16 | Return inspected twice (two agents) | Second inspection: 409 "Already inspected"; gateway still called once | `test_inspecting_a_return_twice_is_refused_and_pays_once` |
| E2E-17 | Inspect before the parcel is received | 409 `invalid_transition` | `test_inspection_before_the_parcel_is_received_is_an_invalid_transition` |
| E2E-18 | Pay a refund still waiting for finance | 409 `refund_not_payable`; gateway not called | `test_paying_a_refund_that_waits_for_finance_is_refused` |
| E2E-19 | Store credit refund | `refunded` without calling the gateway; ledger row with method `store_credit` | `test_store_credit_is_paid_without_calling_the_gateway` |
| E2E-20 | Partial accept | Only the accepted item is refunded | `test_partial_accept_refunds_only_the_accepted_item` |
| E2E-21 | Agent rejects every item | Return `rejected`, refund total 0.00, gateway not called | `test_rejecting_every_item_rejects_the_return_with_no_refund` |
| E2E-22 | Same item submitted twice (double click on Submit) | Second: 409 `duplicate_return` | `test_double_submit_of_the_same_item_is_refused_with_409` |
| E2E-23 | Return more units than were bought | 422 `invalid_return_request` | `test_returning_more_than_was_bought_is_refused` |
| E2E-24 | Mark shipped twice | 409 `invalid_transition` | `test_shipping_twice_is_an_invalid_transition` |
| E2E-25 | Label scanned before the customer marks it shipped | Moves through `in_transit` to `received` | `test_label_scanned_before_shipping_moves_through_in_transit` |
| E2E-26 | Wrong email reads, tracks or ships a return | 404; return unchanged | `test_wrong_email_cannot_read_a_return`, `test_customer_timeline_is_ordered_and_visible_only_to_the_owner`, `test_wrong_email_cannot_mark_a_return_shipped` |
| E2E-27 | Status timeline | Every status in order: requested → approved → in transit → received → inspected → refunded | `test_timeline_lists_every_status_in_order`, `test_customer_timeline_is_ordered_and_visible_only_to_the_owner` · **UI** `customer-return.spec.ts` |
| E2E-28 | Warehouse work queue | A shipped return is in the `in_transit` queue, then moves to `received` | `test_warehouse_queue_moves_a_return_from_in_transit_to_received` |
| E2E-29 | Staff use another role's action | Finance inspecting: 403. Agent reading approvals: 403 | `test_each_role_is_refused_on_the_other_roles_actions` · **UI** `smoke.spec.ts` |
| E2E-30 | Flagged customer returns again | 5th return is created (201); still exactly 1 flag | `test_flagged_customer_can_still_make_a_fifth_return` |
| E2E-31 | Photo upload | PNG accepted and served; a fake image refused with 422; a file over `UPLOAD_MAX_MB` refused with 413 | `test_photo_upload_accepts_png_serves_it_and_refuses_other_files`, `test_photo_larger_than_the_limit_is_refused_with_413` |
| E2E-32 | Audit log | One `STATUS_CHANGE` row per transition, in order | `test_every_status_change_writes_one_audit_row` |
| E2E-33 | Ledger matches paid refunds | `v_ledger_check` returns 0 rows after grade C and store-credit flows | `test_ledger_matches_every_paid_refund_after_mixed_flows` |
| E2E-34 | Label and inspection completeness | Label has a QR code and the warehouse address; an inspection that skips an item is refused (422 `inspection_mismatch`) | `test_label_has_a_qr_code_and_the_warehouse_address`, `test_inspection_must_grade_every_item` |

## Not testable yet

These are phase 2 in `docs/backend-phases.md`. Their endpoints return 501 or do not exist, so their cases are written when the work lands.

- [ ] Manager dashboard: return rate by category, top reasons, average cycle time, flagged customers (`/api/v1/dashboard*`)
- [ ] Audit log endpoints (`/api/v1/audit*`)
- [ ] Metrics, Grafana alert and the gateway-down drill
- [ ] Load test (Locust)
- [ ] UI coverage for E2E-03, 04, 07, 09 and 10: the API cases pass, but no Playwright spec drives them in the browser yet
