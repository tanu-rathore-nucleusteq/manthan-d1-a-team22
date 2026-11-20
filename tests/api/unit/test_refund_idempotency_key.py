"""BR 1.2: every gateway call for a return item uses the key refund-<return_item_id>."""

import pytest

from returnright.domain.refund_policy import refund_idempotency_key


def test_key_is_refund_dash_return_item_id():
    assert refund_idempotency_key(42) == "refund-42"


def test_same_item_always_gets_the_same_key():
    assert refund_idempotency_key(7) == refund_idempotency_key(7)


def test_different_items_get_different_keys():
    assert refund_idempotency_key(7) != refund_idempotency_key(8)


def test_key_fits_the_gateway_header_limits():
    """The gateway accepts keys of 8 to 64 characters."""
    assert 8 <= len(refund_idempotency_key(1)) <= 64
    assert len(refund_idempotency_key(2_147_483_647)) <= 64  # largest SERIAL id


@pytest.mark.parametrize("return_item_id", [0, -1])
def test_return_item_id_must_be_positive(return_item_id):
    with pytest.raises(ValueError, match="positive"):
        refund_idempotency_key(return_item_id)
