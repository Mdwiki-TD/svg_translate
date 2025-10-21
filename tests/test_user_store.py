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
    assert args[6]  # last_used_at timestamp


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
            "last_used_at": "now",
            "rotated_at": None,
        }
    ]
    mock_database.return_value = db_instance

    from src.web.db.user_store import UserTokenStore

    store = UserTokenStore({"host": "", "user": "", "dbname": "", "password": ""}, "test-key")
    user = store.get_user("user-1")

    assert user is not None
    assert user.access_token == "atk"
    assert not user.is_revoked()


@patch("src.web.db.user_store.Database")
def test_revoke_scrubs_credentials(mock_database):
    db_instance = MagicMock()
    mock_database.return_value = db_instance

    from src.web.db.user_store import UserTokenStore

    store = UserTokenStore({"host": "", "user": "", "dbname": "", "password": ""}, "test-key")
    store.revoke("user-1")

    query, params = db_instance.execute_query_safe.call_args[0]
    assert "rotated_at" in query
    assert params[-1] == "user-1"


@patch("src.web.db.user_store.Database")
def test_purge_stale_removes_revoked_and_idle(mock_database):
    db_instance = MagicMock()
    db_instance.execute_query_safe.return_value = 3
    mock_database.return_value = db_instance

    from src.web.db.user_store import UserTokenStore

    store = UserTokenStore({"host": "", "user": "", "dbname": "", "password": ""}, "test-key")
    deleted = store.purge_stale(max_age_days=45)

    assert deleted == 3
    query, params = db_instance.execute_query_safe.call_args[0]
    assert "DELETE FROM user_tokens" in query
    assert "rotated_at IS NOT NULL" in query
    assert params[0]


@patch("src.web.db.user_store.Database")
def test_purge_stale_requires_positive_window(mock_database):
    db_instance = MagicMock()
    mock_database.return_value = db_instance

    from src.web.db.user_store import UserTokenStore

    store = UserTokenStore({"host": "", "user": "", "dbname": "", "password": ""}, "test-key")

    with pytest.raises(ValueError):
        store.purge_stale(max_age_days=0)


def test_invalid_key_raises(monkeypatch):
    from src.web.db.user_store import Fernet, UserTokenStore

    monkeypatch.setattr("src.web.db.user_store.Fernet", MagicMock(side_effect=ValueError("bad key")))

    with pytest.raises(ValueError):
        UserTokenStore({"host": "", "user": "", "dbname": "", "password": ""}, "not-a-key")

    # restore original to avoid leaking patched state
    monkeypatch.setattr("src.web.db.user_store.Fernet", Fernet)
