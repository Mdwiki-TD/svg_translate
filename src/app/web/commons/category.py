
import requests
import logging

from ...config import settings

logger = logging.getLogger(__name__)


def get_category_members(category="Category:Pages using gadget owidslider", project="commons.wikimedia.org", limit=500):
    """
    Fetch all pages belonging to a given category from a Wikimedia project.

    Args:
        category (str): Category title (e.g. 'Category:Pages using gadget owidslider')
        project (str): Domain of wiki (default: commons.wikimedia.org)
        limit (int): Maximum results per request (max 500 for normal users, 5000 for bots)

    Returns:
        list[str]: List of page titles in the category
    """

    api_url = f"https://{project}/w/api.php"
    session = requests.Session()
    session.headers.update({
        "User-Agent": settings.oauth.user_agent
    })

    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": category,
        "cmlimit": limit,
        "format": "json"
    }

    pages = []
    try:
        while True:
            response = session.get(api_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            members = data.get("query", {}).get("categorymembers", [])
            pages.extend([m["title"] for m in members])

            if "continue" in data:
                params["cmcontinue"] = data["continue"]["cmcontinue"]
            else:
                break
    except Exception as e:
        logger.error(f"Error: get_category_members : {e}")

    return pages
