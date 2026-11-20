"""Pays each refund exactly once: unique refund per item, the same idempotency key on every
gateway retry, and a ledger entry. Store credit goes to the ledger only.
"""
