"""Unit tests for OAuth mwclient site builder (no network)."""
from src.app.crypto import encrypt_value
from src.app.wiki_client import build_upload_site


def test_build_upload_site_uses_decrypted_tokens_and_consumer(monkeypatch):
    calls = []

    class DummySite:
        def __init__(self, host, scheme="https", clients_useragent=None,  # pylint: disable=too-many-arguments
                     consumer_token=None, consumer_secret=None,
                     access_token=None, access_secret=None):
            calls.append(
                {
                    "host": host,
                    "scheme": scheme,
                    "clients_useragent": clients_useragent,
                    "consumer_token": consumer_token,
                    "consumer_secret": consumer_secret,
                    "access_token": access_token,
                    "access_secret": access_secret,
                }
            )
            self.host = host
            self.scheme = scheme

    monkeypatch.setattr("src.app.wiki_client.mwclient.Site", DummySite)

    enc_token = encrypt_value("access-key")
    enc_secret = encrypt_value("access-secret")

    site = build_upload_site(enc_token, enc_secret)
    assert isinstance(site, DummySite)
    assert calls and calls[0]["host"] == "commons.wikimedia.org"
    assert calls[0]["scheme"] == "https"
    assert calls[0]["access_token"] == "access-key"  # noqa: S105
    assert calls[0]["access_secret"] == "access-secret"  # noqa: S105
    # consumer creds presence (values come from environment configured by tests/conftest.py)
    assert calls[0]["consumer_token"]
    assert calls[0]["consumer_secret"]