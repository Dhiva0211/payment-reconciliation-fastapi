import enum
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ExceptionStatus(str, enum.Enum):
    MISSING_SETTLEMENT = "MISSING_SETTLEMENT"
    ORPHAN_SETTLEMENT = "ORPHAN_SETTLEMENT"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    DUPLICATE_TRANSACTION = "DUPLICATE_TRANSACTION"


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (Index("ix_payments_reference", "reference"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(64))
    account_id: Mapped[str] = mapped_column(String(32))
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 2))
    currency: Mapped[str] = mapped_column(String(3))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Settlement(Base):
    __tablename__ = "settlements"
    __table_args__ = (Index("ix_settlements_reference", "reference"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(64))
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 2))
    currency: Mapped[str] = mapped_column(String(3))
    settlement_date: Mapped[date] = mapped_column(Date)


class ReconciliationRun(Base):
    __tablename__ = "reconciliation_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    matched: Mapped[int]
    exceptions: Mapped[int]
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ReconciliationException(Base):
    __tablename__ = "reconciliation_exceptions"
    __table_args__ = (
        Index("ix_exceptions_status", "status"),
        Index("ix_exceptions_run", "run_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int]
    reference: Mapped[str] = mapped_column(String(64))
    status: Mapped[ExceptionStatus] = mapped_column(Enum(ExceptionStatus, native_enum=False, length=32))
    detail: Mapped[str] = mapped_column(String(255))
