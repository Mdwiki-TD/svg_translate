import requests
from pathlib import Path
from urllib.parse import quote


def download_commons_svgs(titles, out_dir):
    """
    Download SVG files from Wikimedia Commons.
    Args:
        titles (list): list of filenames (e.g. 'parkinsons-disease-prevalence-ihme,Africa,1990.svg')
        out_dir (str|Path): local folder to save files
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    base = "https://ar.wikipedia.org/wiki/Special:FilePath/"

    session = requests.Session()
    session.headers.update({
        "User-Agent": "WikiMedBot/1.0 (https://meta.wikimedia.org/wiki/User:Mr.Ibrahem; mailto:example@example.org)"
    })
    files = []

    for i, title in enumerate(titles, 1):
        # Construct full URL for direct file access
        url = base + quote(title)
        out_path = out_dir / title

        # Skip if already exists
        if out_path.exists():
            print(f"[{i}] Skipped existing: {title}")
            files.append(out_path)
            continue

        r = session.get(url, timeout=30, allow_redirects=True)
        if r.status_code == 200:  # v and r.content.startswith(b"<?xml")
            print(f"[{i}] Downloaded: {title}")
            out_path.write_bytes(r.content)
            files.append(out_path)
        else:
            print(f"[{i}] Failed (non-SVG or not found): {title}")
    return files

if __name__ == "__main__":
    # Example usage
    titles = [
        "parkinsons-disease-prevalence-ihme,Africa,1990.svg",
        "parkinsons-disease-prevalence-ihme,North America,1991.svg",
    ]
    download_commons_svgs(titles, Path(__file__).parent / "downloaded_svgs")
