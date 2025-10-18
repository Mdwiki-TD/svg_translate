

from svg_translate import download_commons_svgs


from pathlib import Path
tests_files_dir = Path(__file__).parent.parent / "tests_files"

# Example usage
titles = [
    "parkinsons-disease-prevalence-ihme,Africa,1990.svg",
    "parkinsons-disease-prevalence-ihme,North America,1991.svg",
]

download_commons_svgs(titles, tests_files_dir / "downloaded_svgs")
