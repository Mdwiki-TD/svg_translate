

from src.web.download_task import download_one_file

from pathlib import Path
tests_files_dir = Path(__file__).parent.parent / "tests_files"

# Example usage
titles = [
    "parkinsons-disease-prevalence-ihme,Africa,1990.svg",
    "parkinsons-disease-prevalence-ihme,North America,1991.svg",
]

for n, title in enumerate(titles, 1):
    # download_one_file(title: str, out_dir: Path, i: int, session: requests.Session = None)
    download_one_file(title, tests_files_dir, n)
