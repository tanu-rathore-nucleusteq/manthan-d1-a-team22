"""Customer order lookup by order number and email, returning each item's eligibility and reason."""

from fastapi import APIRouter

from returnright.api.deps import OrderServiceDep
from returnright.dtos.requests.orders import OrderLookupRequest
from returnright.dtos.responses.common import ErrorResponse
from returnright.dtos.responses.orders import OrderLookupResponse

router = APIRouter(prefix="/orders", tags=["customer: orders"])


@router.post(
    "/lookup",
    response_model=OrderLookupResponse,
    summary="Find an order and explain which items can be returned",
    responses={
        404: {"model": ErrorResponse, "description": "No order matches this number and email"}
    },
)
def lookup_order(payload: OrderLookupRequest, service: OrderServiceDep) -> OrderLookupResponse:
    return service.lookup(payload.order_number, payload.email)
