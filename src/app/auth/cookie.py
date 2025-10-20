"""Helpers for signing and verifying user identification cookies."""

from __future__ import annotations

from itsdangerous import BadSignature, BadTimeSignature, URLSafeTimedSerializer

from ..config import settings


_serializer = URLSafeTimedSerializer(settings.secret_key, salt="svg-translate-uid")


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
