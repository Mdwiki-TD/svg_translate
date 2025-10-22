import sys
import requests
import tqdm
import mwclient
import types
import wikitextparser
import cryptography
import flask_limiter
import mwoauth
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT/"src"))
    sys.path.insert(0, str(ROOT))

from src import svg_config  # load_dotenv()
