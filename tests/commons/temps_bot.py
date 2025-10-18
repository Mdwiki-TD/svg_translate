
from svg_translate import get_files

from pathlib import Path
tests_files_dir = Path(__file__).parent.parent / "tests_files"

text = (tests_files_dir / "temp.txt").read_text(encoding="utf-8")
main_title, titles = get_files(text)

print("Main title:", main_title)
print("Files count:", len(titles))
print("First 5 files:", titles[:5])
