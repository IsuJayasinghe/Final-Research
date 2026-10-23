"""
Unit tests for Component 2 authentication, password hashing, and JWT tokens.
"""
from datetime import timedelta
import pytest
from fastapi import HTTPException
from backend.drayage.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hashing_and_verification():
    """Verify bcrypt hash generation and validation."""
    plain = "drayage2026"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed) is True
    assert verify_password("wrong_password", hashed) is False


def test_jwt_token_generation_and_decoding():
    """Verify JWT bearer token creation with driver subject claim."""
    token = create_access_token(data={"sub": "DRV-102", "name": "Nalaka Perera"})
    decoded = decode_access_token(token)
    assert decoded["sub"] == "DRV-102"
    assert decoded["name"] == "Nalaka Perera"
    assert "exp" in decoded


def test_expired_jwt_token_rejected():
    """Verify expired JWT tokens raise HTTP 401 Unauthorized."""
    expired_token = create_access_token(
        data={"sub": "DRV-102"},
        expires_delta=timedelta(seconds=-10),  # expired 10 seconds ago
    )
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(expired_token)
    assert exc_info.value.status_code == 401


def test_tampered_jwt_token_rejected():
    """Verify tampered token signatures raise HTTP 401 Unauthorized."""
    token = create_access_token(data={"sub": "DRV-102"})
    tampered = token[:-4] + "abcd"
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(tampered)
    assert exc_info.value.status_code == 401
