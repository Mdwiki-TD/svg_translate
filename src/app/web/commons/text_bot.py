
import requests
import logging

from ...config import settings

logger = logging.getLogger("svg_translate")


def get_wikitext(title, project="commons.wikimedia.org"):
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
        "User-Agent": settings.oauth.user_agent
    })

    params = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "format": "json",
        "titles": title,
    }
    data = {}
    try:
        response = session.get(api_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        logger.error(f"Error: get_wikitext : {e}")

    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        revs = page.get("revisions")
        if revs:
            return revs[0].get("*") or revs[0].get("slots", {}).get("main", {}).get("*")

    return None
