"""Helpers for signing and verifying user identification cookies and state tokens."""

from __future__ import annotations

from itsdangerous import BadSignature, BadTimeSignature, URLSafeTimedSerializer

from ...config import settings


_serializer = URLSafeTimedSerializer(settings.secret_key, salt="svg-translate-uid")

_state_serializer = URLSafeTimedSerializer(
    settings.secret_key, salt="svg-translate-oauth-state"
)


def sign_user_id(user_id: int) -> str:
    """Generate a signed payload for the given user id."""

    return _serializer.dumps({"uid": int(user_id)})


def extract_user_id(token: str) -> int | None:
    """Validate and decode a signed user id token."""

    try:
        data = _serializer.loads(token, max_age=settings.cookie.max_age)
    except (BadSignature, BadTimeSignature):
        return None
    try:
        return int(data.get("uid"))
    except (TypeError, ValueError):
        return None


def sign_state_token(state_nonce: str) -> str:
    """Sign and serialize an OAuth state nonce."""

    return _state_serializer.dumps({"nonce": state_nonce})


def verify_state_token(token: str) -> str | None:
    """Validate a signed OAuth state token and return the embedded nonce."""

    try:
        data = _state_serializer.loads(token, max_age=settings.cookie.max_age)
    except (BadSignature, BadTimeSignature):
        return None
    nonce = data.get("nonce")
    return nonce if isinstance(nonce, str) else None
