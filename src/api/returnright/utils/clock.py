"""Injectable clock (now and today, in UTC) so date-boundary tests can fix the time."""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...

    def today(self) -> date: ...


class SystemClock:
    """The real clock. Every business date is a UTC calendar date."""

    def now(self) -> datetime:
        return datetime.now(UTC)

    def today(self) -> date:
        return self.now().date()


@dataclass(frozen=True, slots=True)
class FixedClock:
    """A clock stopped at one instant, for tests (day 30 versus day 31)."""

    instant: datetime

    def now(self) -> datetime:
        return self.instant

    def today(self) -> date:
        return self.instant.astimezone(UTC).date()


def get_clock() -> Clock:
    """FastAPI dependency; tests override it with a FixedClock."""
    return SystemClock()


def to_utc_date(moment: datetime | None) -> date | None:
    """The UTC calendar date of a timezone-aware timestamp, or None."""
    return moment.astimezone(UTC).date() if moment is not None else None
