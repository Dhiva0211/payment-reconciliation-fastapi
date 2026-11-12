"""Generate a realistic sample batch: 1,500 payments plus settlement data with seeded problems.

Usage:
    python scripts/generate_sample_data.py > sample.json
    # then POST sample["payments"] to /reconciliation/payments and
    # sample["settlements"] to /reconciliation/settlements
"""

import json
import random
from datetime import date, timedelta

random.seed(42)
N_PAYMENTS = 1500


def main() -> None:
    payments, settlements = [], []
    start = date(2026, 1, 1)

    for i in range(N_PAYMENTS):
        ref = f"TXN-{100000 + i}"
        amount = f"{random.uniform(5, 2500):.2f}"
        currency = random.choice(["USD", "USD", "USD", "EUR", "JPY"])
        payments.append({"reference": ref, "account_id": f"ACC-{random.randint(1, 300):04d}",
                         "amount": amount, "currency": currency})

        roll = random.random()
        if roll < 0.03:          # ~3% never settle
            continue
        if roll < 0.05:          # ~2% settle with a different amount
            amount = f"{float(amount) - random.uniform(0.01, 5):.2f}"
        settlements.append({"reference": ref, "amount": amount, "currency": currency,
                            "settlement_date": str(start + timedelta(days=random.randint(0, 30)))})

    for i in range(15):          # duplicated payment references
        dup = random.choice(payments)
        payments.append(dict(dup))
    for i in range(10):          # settlements with no payment
        settlements.append({"reference": f"UNKNOWN-{i}", "amount": "42.00", "currency": "USD",
                            "settlement_date": str(start)})

    print(json.dumps({"payments": payments, "settlements": settlements}, indent=2))


if __name__ == "__main__":
    main()
