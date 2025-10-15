
from pathlib import Path

from commons.download_bot import download_commons_svgs


# Example usage
titles = [
    "parkinsons-disease-prevalence-ihme,Africa,1990.svg",
    "parkinsons-disease-prevalence-ihme,North America,1991.svg",
]
download_commons_svgs(titles, Path(__file__).parent / "downloaded_svgs")
