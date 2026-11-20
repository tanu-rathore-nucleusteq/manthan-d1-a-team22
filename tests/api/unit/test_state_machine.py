"""Only the allowed status moves succeed; everything else is an invalid transition."""

import pytest

from returnright.core.exceptions import InvalidTransitionError
from returnright.domain.enums import ReturnStatus as S
from returnright.domain.state_machine import FINAL_STATUSES, can_move, ensure_can_move

HAPPY_PATH = [S.REQUESTED, S.APPROVED, S.IN_TRANSIT, S.RECEIVED, S.INSPECTED, S.REFUNDED]


@pytest.mark.parametrize(("current", "target"), zip(HAPPY_PATH, HAPPY_PATH[1:], strict=False))
def test_each_step_of_the_happy_path_is_allowed(current, target):
    assert can_move(current, target)


@pytest.mark.parametrize("current", [S.RECEIVED, S.INSPECTED])
def test_rejection_is_allowed_after_receipt_or_inspection(current):
    assert can_move(current, S.REJECTED)


def test_jumping_from_requested_to_refunded_is_an_invalid_transition():
    with pytest.raises(InvalidTransitionError, match="requested, so it can't be marked refunded"):
        ensure_can_move(S.REQUESTED, S.REFUNDED)


def test_marking_shipped_twice_is_an_invalid_transition():
    assert not can_move(S.IN_TRANSIT, S.IN_TRANSIT)


@pytest.mark.parametrize("final", sorted(FINAL_STATUSES))
def test_nothing_moves_out_of_a_final_status(final):
    assert not any(can_move(final, target) for target in S)
