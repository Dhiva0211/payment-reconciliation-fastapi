import pytest
from fastapi import HTTPException

from app.security import authenticate, create_token, decode_token


def test_token_round_trip_keeps_subject_and_roles():
    claims = decode_token(create_token("analyst", ["analyst"]))
    assert claims["sub"] == "analyst"
    assert claims["roles"] == ["analyst"]


def test_tampered_token_is_rejected():
    token = create_token("analyst", ["analyst"])
    with pytest.raises(HTTPException) as exc:
        decode_token(token[:-2] + ("AA" if not token.endswith("AA") else "BB"))
    assert exc.value.status_code == 401


def test_authenticate_rejects_wrong_password_and_unknown_user():
    assert authenticate("admin", "wrong") is None
    assert authenticate("nobody", "password") is None
    assert authenticate("admin", "password") == ["admin"]
