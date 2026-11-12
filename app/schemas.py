from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.models import ExceptionStatus

Currency = Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
Money = Annotated[Decimal, Field(gt=0, max_digits=19, decimal_places=2)]


class PaymentIn(BaseModel):
    reference: str = Field(min_length=1, max_length=64)
    account_id: str = Field(min_length=1, max_length=32)
    amount: Money
    currency: Currency


class SettlementIn(BaseModel):
    reference: str = Field(min_length=1, max_length=64)
    amount: Money
    currency: Currency
    settlement_date: date


class BulkPayments(BaseModel):
    items: list[PaymentIn] = Field(min_length=1, max_length=10_000)


class BulkSettlements(BaseModel):
    items: list[SettlementIn] = Field(min_length=1, max_length=10_000)


class LoadResult(BaseModel):
    loaded: int


class RunSummary(BaseModel):
    run_id: int
    matched: int
    missing_settlement: int
    orphan_settlement: int
    amount_mismatch: int
    duplicate_transaction: int


class ExceptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    reference: str
    status: ExceptionStatus
    detail: str


class ExceptionPage(BaseModel):
    items: list[ExceptionOut]
    total: int
    page: int
    size: int


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
