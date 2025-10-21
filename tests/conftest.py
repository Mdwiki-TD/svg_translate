import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPAT = ROOT / "tests" / "compat"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if COMPAT.exists() and str(COMPAT) not in sys.path:
    sys.path.insert(0, str(COMPAT))

if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")
    exceptions_stub = types.ModuleType("requests.exceptions")
    exceptions_stub.RequestException = Exception
    requests_stub.exceptions = types.SimpleNamespace(RequestException=Exception)

    class _StubSession:
        def __init__(self, *_, **__):
            self.headers = {}

        def get(self, *args, **kwargs):  # pragma: no cover - patched in tests
            return types.SimpleNamespace(status_code=200, content=b"")

    requests_stub.Session = _StubSession
    requests_stub.RequestException = exceptions_stub.RequestException
    sys.modules["requests.exceptions"] = exceptions_stub
    sys.modules["requests"] = requests_stub

if "mwclient" not in sys.modules:
    mwclient_stub = types.ModuleType("mwclient")
    auth_stub = types.ModuleType("mwclient.auth")

    class _OAuthAuth:
        def __init__(self, consumer_key, consumer_secret, access_token, access_secret):
            self.consumer_key = consumer_key
            self.consumer_secret = consumer_secret
            self.access_token = access_token
            self.access_secret = access_secret

    auth_stub.OAuthAuthentication = _OAuthAuth
    mwclient_stub.auth = auth_stub  # type: ignore[attr-defined]
    mwclient_stub.Site = object  # type: ignore[attr-defined]
    sys.modules["mwclient"] = mwclient_stub
    sys.modules["mwclient.auth"] = auth_stub

if "tqdm" not in sys.modules:
    tqdm_stub = types.ModuleType("tqdm")
    tqdm_stub.tqdm = lambda iterable=None, **_: iterable
    sys.modules["tqdm"] = tqdm_stub

if "wikitextparser" not in sys.modules:
    wtp_stub = types.ModuleType("wikitextparser")
    sys.modules["wikitextparser"] = wtp_stub

if "cryptography" not in sys.modules:
    cryptography_stub = types.ModuleType("cryptography")
    fernet_stub = types.ModuleType("cryptography.fernet")

    class _StubFernet:
        def __init__(self, key):  # pragma: no cover - stub for tests
            self._key = key

        def encrypt(self, data):
            payload = data if isinstance(data, bytes) else data.encode()
            return b"stub:" + payload

        def decrypt(self, token):
            if not token.startswith(b"stub:"):
                raise Exception("Invalid token")
            return token[5:]

    class _InvalidToken(Exception):
        pass

    fernet_stub.Fernet = _StubFernet
    fernet_stub.InvalidToken = _InvalidToken
    sys.modules["cryptography"] = cryptography_stub
    sys.modules["cryptography.fernet"] = fernet_stub

if "flask_limiter" not in sys.modules:
    from functools import wraps

    limiter_stub = types.ModuleType("flask_limiter")
    limiter_util_stub = types.ModuleType("flask_limiter.util")

    class _StubLimiter:
        def __init__(self, app=None, key_func=None, storage_uri=None, key_prefix=None, default_limits=None):
            self.app = app
            self.key_func = key_func or (lambda: "global")
            self.storage_uri = storage_uri
            self.key_prefix = key_prefix
            self.default_limits = default_limits
            self._hits = {}

        def limit(self, limit_value):  # pragma: no cover - simple stub
            parts = str(limit_value).split("/")
            try:
                max_calls = int(parts[0])
            except (ValueError, TypeError):
                max_calls = 1

            def decorator(fn):
                endpoint = getattr(fn, "__name__", str(id(fn)))

                @wraps(fn)
                def wrapper(*args, **kwargs):
                    key = (endpoint, self.key_func() if callable(self.key_func) else self.key_func)
                    hits = self._hits.get(key, 0)
                    if hits >= max_calls:
                        from flask import Response

                        return Response("Rate limit exceeded", status=429)

                    self._hits[key] = hits + 1
                    return fn(*args, **kwargs)

                return wrapper

            return decorator

    def _get_remote_address():  # pragma: no cover - behaviour exercised indirectly
        return "127.0.0.1"

    limiter_stub.Limiter = _StubLimiter
    limiter_util_stub.get_remote_address = _get_remote_address
    sys.modules["flask_limiter"] = limiter_stub
    sys.modules["flask_limiter.util"] = limiter_util_stub

if "mwoauth" not in sys.modules:
    mwoauth_stub = types.ModuleType("mwoauth")

    class _RequestToken:
        def __init__(self, key, secret):
            self.key = key
            self.secret = secret

    class _AccessToken(_RequestToken):
        pass

    class _ConsumerToken(_RequestToken):
        pass

    class _Handshaker:
        def __init__(self, *_args, **_kwargs):
            self.consumer_token = _kwargs.get("consumer_token")
            self.last_initiate = {}

        def initiate(self, callback=None, params=None):  # pragma: no cover - behaviour verified in tests
            self.last_initiate = {"callback": callback, "params": params}
            return "https://example.org/oauth", _RequestToken("request", "secret")

        def complete(self, request_token, _query):
            return _AccessToken("access", "secret")

        def identify(self, _access_token):
            return {"sub": "user-1", "username": "TestUser"}

    mwoauth_stub.RequestToken = _RequestToken
    mwoauth_stub.AccessToken = _AccessToken
    mwoauth_stub.ConsumerToken = _ConsumerToken
    mwoauth_stub.Handshaker = _Handshaker

    sys.modules["mwoauth"] = mwoauth_stub


