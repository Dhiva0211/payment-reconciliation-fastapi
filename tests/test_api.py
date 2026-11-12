from tests.conftest import auth_header


def payment(ref: str, amount: str, currency: str = "USD") -> dict:
    return {"reference": ref, "account_id": "ACC-1", "amount": amount, "currency": currency}


def settlement(ref: str, amount: str, currency: str = "USD") -> dict:
    return {"reference": ref, "amount": amount, "currency": currency, "settlement_date": "2026-01-15"}


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_login_with_bad_password_is_unauthorized(client):
    resp = client.post("/auth/token", data={"username": "admin", "password": "nope"})
    assert resp.status_code == 401


def test_requests_without_token_are_unauthorized(client):
    assert client.get("/reconciliation/exceptions").status_code == 401


def test_analyst_cannot_load_payments(client):
    resp = client.post("/reconciliation/payments", json={"items": [payment("A", "1.00")]},
                       headers=auth_header(client, "analyst"))
    assert resp.status_code == 403


def test_operator_can_load_payments(client):
    resp = client.post("/reconciliation/payments", json={"items": [payment("A", "1.00")]},
                       headers=auth_header(client, "operator"))
    assert resp.status_code == 201
    assert resp.json() == {"loaded": 1}


def test_invalid_currency_and_amount_are_rejected(client):
    resp = client.post("/reconciliation/payments",
                       json={"items": [payment("A", "-5.00", "usd")]},
                       headers=auth_header(client, "operator"))
    assert resp.status_code == 422


def test_full_reconciliation_run(client):
    op, admin = auth_header(client, "operator"), auth_header(client, "admin")
    client.post("/reconciliation/payments", headers=op, json={"items": [
        payment("OK-1", "10.00"), payment("MISS-1", "5.00"), payment("BAD-1", "75.00"),
        payment("DUP-1", "3.00"), payment("DUP-1", "3.00"),
    ]})
    client.post("/reconciliation/settlements", headers=op, json={"items": [
        settlement("OK-1", "10.00"), settlement("BAD-1", "70.00"), settlement("ORPHAN-1", "9.99"),
    ]})

    assert client.post("/reconciliation/runs", headers=op).status_code == 403
    summary = client.post("/reconciliation/runs", headers=admin).json()

    assert summary["matched"] == 1
    assert summary["missing_settlement"] == 1
    assert summary["amount_mismatch"] == 1
    assert summary["orphan_settlement"] == 1
    assert summary["duplicate_transaction"] == 1


def test_exceptions_are_paginated_and_filterable(client):
    op, analyst = auth_header(client, "operator"), auth_header(client, "analyst")
    client.post("/reconciliation/payments", headers=op,
                json={"items": [payment(f"P-{i}", "1.00") for i in range(7)]})
    client.post("/reconciliation/runs", headers=auth_header(client, "admin"))

    page1 = client.get("/reconciliation/exceptions", params={"size": 5, "page": 1}, headers=analyst).json()
    page2 = client.get("/reconciliation/exceptions", params={"size": 5, "page": 2}, headers=analyst).json()
    assert page1["total"] == 7 and len(page1["items"]) == 5 and len(page2["items"]) == 2

    filtered = client.get("/reconciliation/exceptions", params={"status": "ORPHAN_SETTLEMENT"},
                          headers=analyst).json()
    assert filtered["total"] == 0
