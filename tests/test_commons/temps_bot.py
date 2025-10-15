
from pathlib import Path

Dir = Path(__file__).parent

from commons.temps_bot import get_files

text = (Dir / "temp.txt").read_text(encoding="utf-8")
main_title, titles = get_files(text)

print("Main title:", main_title)
print("Files count:", len(titles))
print("First 5 files:", titles[:5])
