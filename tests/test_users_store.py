"""Tests for the user token persistence helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.app.users import store


@pytest.fixture(autouse=True)
def reset_db(monkeypatch):
    monkeypatch.setattr(store, "_db", None)


def test_mark_token_used_updates_last_used(monkeypatch):
    fake_db = MagicMock()
    monkeypatch.setattr(store, "_get_db", lambda: fake_db)

    store.mark_token_used(12)

    fake_db.execute_query.assert_called_once()
    executed_sql = fake_db.execute_query.call_args[0][0]
    assert "last_used_at = CURRENT_TIMESTAMP" in executed_sql


def test_user_token_record_decrypted_marks_usage(monkeypatch):
    monkeypatch.setattr(store, "decrypt_value", lambda value: value.decode("utf-8"))
    calls: list[int] = []
    monkeypatch.setattr(store, "mark_token_used", lambda user_id: calls.append(user_id))

    record = store.UserTokenRecord(
        user_id=3,
        username="Tester",
        access_token=b"token",
        access_secret=b"secret",
    )

    decrypted = record.decrypted()

    assert decrypted == ("token", "secret")
    assert calls == [3]
