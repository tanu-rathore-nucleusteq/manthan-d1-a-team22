"""Customer order lookup by order number and email, returning each item's eligibility and reason."""

from fastapi import APIRouter

from returnright.api.deps import DbSession
from returnright.api.not_implemented import not_implemented
from returnright.dtos.requests.orders import OrderLookupRequest
from returnright.dtos.responses.orders import OrderLookupResponse

router = APIRouter(prefix="/orders", tags=["customer: orders"])


@router.post(
    "/lookup",
    response_model=OrderLookupResponse,
    summary="Find an order and explain which items can be returned",
    responses={404: {"description": "No order matches this number and email"}},
)
def lookup_order(payload: OrderLookupRequest, db: DbSession) -> OrderLookupResponse:
    not_implemented("Order lookup")
