"""Pays each refund exactly once: one refund per return item, the key refund-<return_item_id> on
every gateway call, and one ledger row. Store credit goes to the ledger only, never the gateway.
A gateway error marks the refund failed and a retry reuses the same key; a timeout is retried the
same way, because the gateway replays its first answer for a key it has already paid.
"""
