"""Insert-only audit log: one row per state change (who, what, from, to, when). Return events
carry return_id, which powers the customer's status timeline.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from returnright.models.base import Base

STATUS_CHANGE = "STATUS_CHANGE"


class AuditLog(Base):
    __tablename__ = "audit_log"

    audit_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    return_id: Mapped[int | None] = mapped_column(ForeignKey("returns.return_id"))
    entity_type: Mapped[str] = mapped_column(String(30))
    entity_id: Mapped[int]
    action: Mapped[str] = mapped_column(String(30))
    old_status: Mapped[str | None] = mapped_column(String(20))
    new_status: Mapped[str | None] = mapped_column(String(20))
    actor_type: Mapped[str] = mapped_column(String(10))
    actor_id: Mapped[int | None]
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
