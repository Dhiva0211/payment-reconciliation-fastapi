from dataclasses import dataclass
from decimal import Decimal

from app.models import ExceptionStatus as S
from app.reconciliation import reconcile


@dataclass
class Rec:
    reference: str
    amount: Decimal
    currency: str = "USD"


def d(value: str) -> Decimal:
    return Decimal(value)


def test_matching_payment_and_settlement():
    result = reconcile([Rec("A", d("10.00"))], [Rec("A", d("10.00"))])
    assert result.matched == 1
    assert result.findings == []


def test_decimal_scale_does_not_cause_false_mismatch():
    result = reconcile([Rec("A", d("100.0"))], [Rec("A", d("100.00"))])
    assert result.matched == 1


def test_missing_settlement_is_flagged():
    result = reconcile([Rec("A", d("5.00"))], [])
    assert result.count(S.MISSING_SETTLEMENT) == 1


def test_amount_mismatch_is_flagged_with_both_amounts():
    result = reconcile([Rec("A", d("75.00"))], [Rec("A", d("70.00"))])
    assert result.count(S.AMOUNT_MISMATCH) == 1
    assert "75.00" in result.findings[0].detail and "70.00" in result.findings[0].detail


def test_currency_mismatch_is_flagged():
    result = reconcile([Rec("A", d("20.00"), "USD")], [Rec("A", d("20.00"), "EUR")])
    assert result.count(S.AMOUNT_MISMATCH) == 1


def test_orphan_settlement_is_flagged():
    result = reconcile([], [Rec("Z", d("1.00"))])
    assert result.count(S.ORPHAN_SETTLEMENT) == 1
    assert result.findings[0].reference == "Z"


def test_duplicate_payments_reported_once_and_not_matched():
    result = reconcile([Rec("A", d("30.00")), Rec("A", d("30.00"))], [Rec("A", d("30.00"))])
    assert result.count(S.DUPLICATE_TRANSACTION) == 1
    assert result.matched == 0
