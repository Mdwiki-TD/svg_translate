#
import os
import sys
from cryptography.fernet import Fernet
from pathlib import Path
import secrets
ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT/"src"))
    sys.path.insert(0, str(ROOT))
# ---
CopySvgTranslate_PATH = os.getenv("CopySvgTranslate_PATH", "I:/SVG_PY/CopySvgTranslate/CopySvgTranslate")
# ---
if CopySvgTranslate_PATH and Path(CopySvgTranslate_PATH).is_dir():
    sys.path.insert(0, str(Path(CopySvgTranslate_PATH).parent))
# ---
os.environ.setdefault("FLASK_SECRET_KEY", secrets.token_hex(16))
os.environ.setdefault("OAUTH_ENCRYPTION_KEY", Fernet.generate_key().decode("utf-8"))
os.environ.setdefault("OAUTH_CONSUMER_KEY", "test-consumer-key")
os.environ.setdefault("OAUTH_CONSUMER_SECRET", "test-consumer-secret")
os.environ.setdefault("OAUTH_MWURI", "https://example.org/w/index.php")

from src.app import svg_config  # load_dotenv()
