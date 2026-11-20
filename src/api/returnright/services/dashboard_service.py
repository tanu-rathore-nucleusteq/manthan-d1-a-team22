"""Manager dashboard: return rate by category, top reasons, average cycle time and flagged
customers, optionally limited to a date range. Read-only.
"""

from datetime import date

from sqlalchemy.orm import Session

from returnright.core.exceptions import InvalidDateRangeError
from returnright.domain.customer_flags import window_starts_on
from returnright.dtos.responses.dashboard import (
    CategoryReturnRateResponse,
    DashboardResponse,
    FlaggedCustomerResponse,
    ReasonCountResponse,
)
from returnright.mappers.dashboard_mapper import (
    to_category_rate,
    to_flagged_customer,
    to_reason_count,
)
from returnright.repositories.dashboard_repository import DashboardRepository
from returnright.utils.clock import Clock


class DashboardService:
    def __init__(self, session: Session, clock: Clock) -> None:
        self._metrics = DashboardRepository(session)
        self._clock = clock

    def dashboard(self, date_from: date | None, date_to: date | None) -> DashboardResponse:
        _check_range(date_from, date_to)
        return DashboardResponse(
            return_rate_by_category=self.return_rates(date_from, date_to),
            # Every reason that was used, so the web app can show each one's share of the total.
            top_reasons=self._reasons(date_from, date_to, limit=None),
            average_cycle_time_hours=self._metrics.average_cycle_hours(date_from, date_to),
            flagged_customers=self.flagged_customers(),
            generated_at=self._clock.now(),
        )

    def return_rates(
        self, date_from: date | None, date_to: date | None
    ) -> list[CategoryReturnRateResponse]:
        _check_range(date_from, date_to)
        rates = map(to_category_rate, self._metrics.category_counts(date_from, date_to))
        return sorted(rates, key=lambda rate: rate.return_rate, reverse=True)

    def top_reasons(
        self, date_from: date | None, date_to: date | None, limit: int
    ) -> list[ReasonCountResponse]:
        _check_range(date_from, date_to)
        return self._reasons(date_from, date_to, limit)

    def flagged_customers(self) -> list[FlaggedCustomerResponse]:
        start = window_starts_on(self._clock.today())
        return [to_flagged_customer(row) for row in self._metrics.flagged_customers(start)]

    def _reasons(
        self, date_from: date | None, date_to: date | None, limit: int | None
    ) -> list[ReasonCountResponse]:
        rows = self._metrics.reason_counts(date_from, date_to, limit)
        return [to_reason_count(code, count) for code, count in rows]


def _check_range(date_from: date | None, date_to: date | None) -> None:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise InvalidDateRangeError()
