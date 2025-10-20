"""Tests for the encrypted user token store."""

from unittest.mock import MagicMock, patch

import pytest


@patch("src.web.db.user_store.Database")
def test_upsert_credentials_encrypts_tokens(mock_database):
    db_instance = MagicMock()
    mock_database.return_value = db_instance

    from src.web.db.user_store import UserTokenStore

    store = UserTokenStore({"host": "", "user": "", "dbname": "", "password": ""}, "test-key")
    store.upsert_credentials("user-1", "Tester", "atk", "ats")

    args = db_instance.execute_query_safe.call_args[0][1]
    assert args[0] == "user-1"
    assert args[1] == "Tester"
    assert args[2].startswith(b"stub:")
    assert args[3].startswith(b"stub:")


@patch("src.web.db.user_store.Database")
def test_get_user_decrypts_payload(mock_database):
    db_instance = MagicMock()
    db_instance.fetch_query_safe.return_value = [
        {
            "user_id": "user-1",
            "username": "Tester",
            "access_token": b"stub:atk",
            "access_secret": b"stub:ats",
            "created_at": "now",
            "updated_at": "now",
        }
    ]
    mock_database.return_value = db_instance

    from src.web.db.user_store import UserTokenStore

    store = UserTokenStore({"host": "", "user": "", "dbname": "", "password": ""}, "test-key")
    user = store.get_user("user-1")

    assert user is not None
    assert user.access_token == "atk"
    assert user.access_secret == "ats"
