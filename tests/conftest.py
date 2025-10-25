import sys

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT/"src"))
    sys.path.insert(0, str(ROOT))

from src.app import svg_config  # load_dotenv()
