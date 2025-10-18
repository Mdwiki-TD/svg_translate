import requests
from pathlib import Path
from urllib.parse import quote
from tqdm import tqdm


from ..log import logger


def download_commons_svgs(titles, out_dir):
    """
    Download SVG files from Wikimedia Commons.
    Args:
        titles (list): list of filenames (e.g. 'parkinsons-disease-prevalence-ihme,Africa,1990.svg')
        out_dir (str|Path): local folder to save files
    """
    out_dir = Path(str(out_dir))
    out_dir.mkdir(parents=True, exist_ok=True)

    # base = "https://commons.wikimedia.org/wiki/Special:FilePath/" # commons is blocked in Yemen
    base = "https://ar.wikipedia.org/wiki/Special:FilePath/"

    session = requests.Session()
    session.headers.update({
        "User-Agent": "WikiMedBot/1.0 (https://meta.wikimedia.org/wiki/User:Mr.Ibrahem; mailto:example@example.org)"
    })
    files = []

    existing = 0
    failed = 0
    success = 0

    # titles = list(set(titles))

    for i, title in tqdm(enumerate(titles, 1), total=len(titles), desc="Downloading files"):
        # Construct full URL for direct file access
        url = base + quote(title)
        out_path = out_dir / title

        # Skip if already exists
        if out_path.exists():
            logger.debug(f"[{i}] Skipped existing: {title}")
            existing += 1
            files.append(out_path)
            continue

        try:
            r = session.get(url, timeout=30, allow_redirects=True)
        except requests.RequestException as exc:
            failed += 1
            logger.error(f"[{i}] Failed (network error): {title} -> {exc}")
            continue

        # if r.status_code == 200 and 'image/svg+xml' in r.headers.get('Content-Type', ''):

        if r.status_code == 200:  # v and r.content.startswith(b"<?xml")
            logger.debug(f"[{i}] Downloaded: {title}")
            out_path.write_bytes(r.content)
            success += 1
            files.append(out_path)
        else:
            failed += 1
            logger.error(f"[{i}] Failed (non-SVG or not found): {title}")

    logger.info(f"Downloaded {success} files, skipped {existing} existing files, failed to download {failed} files")

    return files
