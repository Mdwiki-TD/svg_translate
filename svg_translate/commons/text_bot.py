
import requests

from ..log import logger


def get_wikitext(title, project="commons.m.wikimedia.org"):
    """
    Fetch raw wikitext of a page from Wikimedia projects.
    Args:
        title (str): Page title (e.g. 'Template:OWID/Parkinsons prevalence')
        project (str): Domain of wiki (default: commons.wikimedia.org)
    Returns:
        str: wikitext content or None if not found
    """
    api_url = f"https://{project}/w/api.php"
    session = requests.Session()
    session.headers.update({
        "User-Agent": "WikiMedBot/1.0 (https://meta.wikimedia.org/wiki/User:Mr.Ibrahem; mailto:example@example.org)"
    })

    params = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "format": "json",
        "titles": title,
    }

    try:
        response = session.get(api_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            revs = page.get("revisions")
            if revs:
                return revs[0].get("*") or revs[0].get("slots", {}).get("main", {}).get("*")
    except Exception as e:
        logger.error("Error: get_wikitext :", e)

    return None
