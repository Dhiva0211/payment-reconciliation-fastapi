"""Pure reconciliation logic, kept free of database code so it is easy to unit test."""

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.models import ExceptionStatus


class PaymentLike(Protocol):
    reference: str
    amount: Decimal
    currency: str


class SettlementLike(Protocol):
    reference: str
    amount: Decimal
    currency: str


@dataclass(frozen=True)
class Finding:
    reference: str
    status: ExceptionStatus
    detail: str


@dataclass(frozen=True)
class Result:
    matched: int
    findings: list[Finding]

    def count(self, status: ExceptionStatus) -> int:
        return sum(1 for f in self.findings if f.status is status)


def reconcile(payments: list[PaymentLike], settlements: list[SettlementLike]) -> Result:
    """Match payments to settlements by reference.

    A reference that appears on more than one payment is reported once as a duplicate and is
    not matched. Amounts are compared as Decimals so 100.0 and 100.00 are equal.
    """
    by_ref: dict[str, list[PaymentLike]] = defaultdict(list)
    for p in payments:
        by_ref[p.reference].append(p)

    settled: dict[str, SettlementLike] = {}
    for s in settlements:
        settled.setdefault(s.reference, s)

    findings: list[Finding] = []
    matched = 0

    for ref, group in by_ref.items():
        if len(group) > 1:
            findings.append(Finding(ref, ExceptionStatus.DUPLICATE_TRANSACTION,
                                    f"{len(group)} payments share this reference"))
            continue
        payment = group[0]
        settlement = settled.get(ref)
        if settlement is None:
            findings.append(Finding(ref, ExceptionStatus.MISSING_SETTLEMENT, "No settlement received"))
        elif Decimal(payment.amount) != Decimal(settlement.amount) or payment.currency != settlement.currency:
            findings.append(Finding(
                ref, ExceptionStatus.AMOUNT_MISMATCH,
                f"Payment {payment.amount} {payment.currency} vs settled {settlement.amount} {settlement.currency}",
            ))
        else:
            matched += 1

    for ref in settled.keys() - by_ref.keys():
        findings.append(Finding(ref, ExceptionStatus.ORPHAN_SETTLEMENT, "Settlement has no matching payment"))

    return Result(matched=matched, findings=findings)
