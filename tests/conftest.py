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
    sys.modules["requests.exceptions"] = exceptions_stub
    sys.modules["requests"] = requests_stub

if "mwclient" not in sys.modules:
    mwclient_stub = types.ModuleType("mwclient")
    mwclient_stub.Site = object  # type: ignore[attr-defined]
    sys.modules["mwclient"] = mwclient_stub

if "tqdm" not in sys.modules:
    tqdm_stub = types.ModuleType("tqdm")
    tqdm_stub.tqdm = lambda iterable=None, **_: iterable
    sys.modules["tqdm"] = tqdm_stub

if "wikitextparser" not in sys.modules:
    wtp_stub = types.ModuleType("wikitextparser")
    sys.modules["wikitextparser"] = wtp_stub


