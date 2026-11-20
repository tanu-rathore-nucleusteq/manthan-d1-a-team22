# ADR-001: Refunds are idempotent at two layers, and finance approves per return

- Status: accepted
- Date: 2026-11-20
- Deciders: ReturnRight team (BE-1, BE-2, FE, QA)

## Context

The retailer has paid duplicate refunds. A refund can be sent twice in three ways: a reviewer or customer clicks twice, the browser or our code retries a request, or the gateway times out after it has already taken the money and we retry. The use case asks us to choose between an idempotency key and a unique refund per return item.

Separately, the use case says "a finance reviewer approves refunds above 10,000 INR". This can be read per item or per return.

## Options

| Option | Protects against | Misses |
| --- | --- | --- |
| A. Idempotency key on the gateway call | Retries and timeouts at the gateway | Our own bug creating a second refund row with a new key |
| B. Unique refund per return item in the database | A second refund row, whatever the code does | A retry after a timeout reaching the gateway twice |
| A + B | All three | Slightly more code |

## Decision

1. **Use both.** The database allows one refund per return item (`refunds.return_item_id UNIQUE`). The refund's key is `refund-<return_item_id>`, stored on the row (`refunds.idempotency_key UNIQUE`) and sent on every gateway call, including every retry. The gateway stores keys (`gateway.payments.idempotency_key UNIQUE`) and replays its first answer for a repeated key.
2. **The ledger has one refund row per refund** (`UNIQUE (refund_id, entry_type)`), is insert-only (a trigger blocks updates and deletes), and corrections are reversal rows.
3. **A failed payment is retried with the same key.** A gateway error sets the refund to `failed`; `POST /finance/refunds/{id}/pay` retries it. A timeout is handled the same way: if the gateway had already paid, the retry gets the replayed answer and nothing is paid twice.
4. **Store credit never calls the gateway.** It is paid by writing the ledger row.
5. **Finance approves per return.** The threshold applies to the return's refund total, strictly above 10,000 INR, so splitting a return into items can't avoid approval (two items at 6,000 each wait for finance). There is one decision per return (`finance_approvals.return_id UNIQUE`).

## Consequences

- A double click, a concurrent request, a browser retry and a retry after a timeout all end with one refund, one gateway payment and one ledger row. Integration tests cover each case.
- The gateway call happens outside the database transaction: the refund is marked `processing` and committed first, then the gateway is called, then the result and the ledger row are committed together.
- The check "ledger total equals paid refunds" is a database view (`v_ledger_check`) that must always return no rows.
