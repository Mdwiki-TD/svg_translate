"""Unit tests for cryptographic helpers."""
import pytest
from src.app.crypto import encrypt_value, decrypt_value


def test_encrypt_decrypt_roundtrip():
    msg = "secret message"
    token = encrypt_value(msg)
    assert isinstance(token, (bytes, bytearray))
    plain = decrypt_value(token)
    assert plain == msg


def test_decrypt_invalid_token_raises():
    with pytest.raises(ValueError):
        decrypt_value(b"not-a-valid-fernet-token")