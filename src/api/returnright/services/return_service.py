"""Customer returns: create (eligibility re-checked, duplicates refused, frequent returners
flagged), detail and timeline, QR label, mark shipped and photo upload. Every customer call
proves ownership with the order's email.
"""

from datetime import timedelta
from typing import BinaryIO

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from returnright.core.config import Settings
from returnright.core.exceptions import (
    DuplicateReturnError,
    InvalidReturnRequestError,
    ItemNotEligibleError,
    LabelUnavailableError,
    OrderNotFoundError,
    PhotoRejectedError,
    ReturnNotFoundError,
)
from returnright.domain.customer_flags import FLAG_WINDOW_DAYS, should_flag
from returnright.domain.enums import ReturnStatus
from returnright.dtos.internal.audit import Actor
from returnright.dtos.requests.returns import CreateReturnRequest
from returnright.dtos.responses.returns import (
    PhotoUploadResponse,
    ReturnDetailResponse,
    ReturnLabelResponse,
    StatusEventResponse,
)
from returnright.mappers.return_mapper import photo_url, to_return_detail, to_status_events
from returnright.models.customer import CustomerFlag
from returnright.models.return_request import ReturnItem, ReturnPhoto, ReturnRequest
from returnright.repositories.audit_repository import AuditRepository
from returnright.repositories.customer_repository import CustomerRepository
from returnright.repositories.order_repository import OrderRepository
from returnright.repositories.return_repository import ReturnRepository
from returnright.services.audit_service import AuditTrail, ReturnTransitions
from returnright.services.label_service import qr_svg
from returnright.services.order_service import decide_items
from returnright.services.storage_service import PhotoStorage
from returnright.utils.clock import Clock
from returnright.utils.ids import new_return_code

ELIGIBILITY_REASON_MAX = 300
PHOTO_STATUSES = {ReturnStatus.REQUESTED, ReturnStatus.APPROVED, ReturnStatus.IN_TRANSIT}


class ReturnService:
    def __init__(self, session: Session, settings: Settings, clock: Clock) -> None:
        self._session = session
        self._settings = settings
        self._clock = clock
        self._orders = OrderRepository(session)
        self._returns = ReturnRepository(session)
        self._customers = CustomerRepository(session)
        self._audits = AuditRepository(session)
        self._audit = AuditTrail(self._audits)
        self._transitions = ReturnTransitions(self._audit, clock)
        self._storage = PhotoStorage(settings.upload_dir, settings.upload_max_mb, clock)

    # --- create ------------------------------------------------------------------------------

    def create(self, payload: CreateReturnRequest) -> ReturnDetailResponse:
        order = self._orders.find_by_number_and_email(payload.order_number, payload.email)
        if order is None:
            raise OrderNotFoundError()

        order_items = {item.order_item_id: item for item in order.items}
        requested_ids = [item.order_item_id for item in payload.items]
        if len(set(requested_ids)) != len(requested_ids):
            raise InvalidReturnRequestError("Each item can only be listed once.")
        unknown = [item_id for item_id in requested_ids if item_id not in order_items]
        if unknown:
            raise InvalidReturnRequestError("Some of these items are not part of this order.")
        for requested in payload.items:
            bought = order_items[requested.order_item_id]
            if requested.quantity > bought.quantity:
                raise InvalidReturnRequestError(
                    f"You bought {bought.quantity} of {bought.product.name}, so you can return "
                    f"at most {bought.quantity}."
                )

        decisions = decide_items(order, self._clock)
        refused = [
            f"{order_items[item_id].product.name}: {decisions[item_id].reason}"
            for item_id in requested_ids
            if not decisions[item_id].eligible
        ]
        if refused:
            raise ItemNotEligibleError(" ".join(refused))
        if self._returns.order_items_already_returned(requested_ids):
            raise DuplicateReturnError()

        reason_ids = self._returns.reason_ids()
        code = new_return_code()
        now = self._clock.now()
        return_request = ReturnRequest(
            return_code=code,
            label_code=code,
            order_id=order.order_id,
            customer_id=order.customer_id,
            status=ReturnStatus.REQUESTED,
            refund_method=payload.refund_method,
            awaiting_finance=False,
            requested_at=now,
            items=[
                ReturnItem(
                    order_item_id=requested.order_item_id,
                    quantity=requested.quantity,
                    reason_id=reason_ids[requested.reason.name],
                    reason_note=requested.reason_details,
                    days_since_delivery=decisions[requested.order_item_id].days_since_delivery,
                    is_eligible=True,
                    eligibility_reason=decisions[requested.order_item_id].reason[
                        :ELIGIBILITY_REASON_MAX
                    ],
                )
                for requested in payload.items
            ],
        )
        self._returns.add(return_request)
        try:
            self._session.flush()
        except IntegrityError as error:  # the same item submitted twice at the same moment
            self._session.rollback()
            raise DuplicateReturnError() from error

        self._transitions.open(return_request, Actor.customer(order.customer_id, payload.email))
        self._transitions.move(
            return_request,
            ReturnStatus.APPROVED,
            Actor.system(),
            note="Every item is within its return window.",
        )
        self._flag_frequent_returner(return_request)
        self._session.commit()
        return self._detail(self._returns.get_by_id(return_request.return_id))

    def _flag_frequent_returner(self, return_request: ReturnRequest) -> None:
        since = return_request.requested_at - timedelta(days=FLAG_WINDOW_DAYS)
        count = self._returns.count_customer_returns_since(return_request.customer_id, since)
        if not should_flag(count) or self._customers.has_open_flag(return_request.customer_id):
            return
        customer = self._customers.get(return_request.customer_id)
        customer.is_flagged = True
        self._customers.add_flag(
            CustomerFlag(
                customer_id=customer.customer_id,
                trigger_return_id=return_request.return_id,
                returns_in_30d=count,
            )
        )
        self._audit.record(
            entity_type="CUSTOMER",
            entity_id=customer.customer_id,
            return_id=return_request.return_id,
            action="FLAGGED",
            actor=Actor.system(),
            details={"returns_in_30_days": count},
        )

    # --- read --------------------------------------------------------------------------------

    def detail(self, code: str, email: str) -> ReturnDetailResponse:
        return self._detail(self._owned(code, email))

    def timeline(self, code: str, email: str) -> list[StatusEventResponse]:
        return_request = self._owned(code, email)
        return to_status_events(self._audits.status_history(return_request.return_id))

    def label(self, code: str, email: str) -> ReturnLabelResponse:
        return_request = self._owned(code, email)
        if return_request.status == ReturnStatus.REJECTED:
            raise LabelUnavailableError()
        return ReturnLabelResponse(
            return_code=return_request.return_code,
            qr_svg=qr_svg(return_request.return_code),
            ship_to=self._settings.warehouse_address,
        )

    # --- customer actions --------------------------------------------------------------------

    def ship(self, code: str, email: str) -> ReturnDetailResponse:
        return_request = self._owned(code, email, for_update=True)
        self._transitions.move(
            return_request,
            ReturnStatus.IN_TRANSIT,
            Actor.customer(return_request.customer_id, email),
            note="The customer shipped the parcel.",
        )
        self._session.commit()
        return self._detail(self._returns.get_by_id(return_request.return_id))

    def upload_photo(
        self, code: str, email: str, return_item_id: int, stream: BinaryIO
    ) -> PhotoUploadResponse:
        return_request = self._owned(code, email, for_update=True)
        if return_request.status not in PHOTO_STATUSES:
            raise PhotoRejectedError(
                "Photos can only be added before the warehouse receives the parcel."
            )
        item = next(
            (item for item in return_request.items if item.return_item_id == return_item_id),
            None,
        )
        if item is None:
            raise PhotoRejectedError("That item is not part of this return.")
        if len(item.photos) >= self._settings.photos_per_item_max:
            raise PhotoRejectedError(
                f"Each item can have at most {self._settings.photos_per_item_max} photos."
            )

        stored = self._storage.save(stream)
        self._session.add(
            ReturnPhoto(return_item_id=item.return_item_id, file_path=stored.relative_path)
        )
        self._session.commit()
        return PhotoUploadResponse(
            return_code=return_request.return_code,
            return_item_id=item.return_item_id,
            photo_url=photo_url(stored.relative_path),
            content_type=stored.content_type,
            size_bytes=stored.size_bytes,
        )

    # --- helpers -----------------------------------------------------------------------------

    def _owned(self, code: str, email: str, *, for_update: bool = False) -> ReturnRequest:
        """The return, if this email owns it. A wrong code and a wrong email look the same."""
        return_request = self._returns.get_by_code(code, for_update=for_update)
        if return_request is None or return_request.customer.email.lower() != email.lower():
            raise ReturnNotFoundError()
        return return_request

    def _detail(self, return_request: ReturnRequest) -> ReturnDetailResponse:
        return to_return_detail(
            return_request, self._audits.status_history(return_request.return_id)
        )
