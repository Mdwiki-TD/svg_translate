"""Test-friendly proxy that reads credentials from the src layout."""

try:
    from src.user_info import password, username  # type: ignore
except ImportError:  # pragma: no cover - fallback when src module missing
    username = ""
    password = ""

__all__ = ["username", "password"]
