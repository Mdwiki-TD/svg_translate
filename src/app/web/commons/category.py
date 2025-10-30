
import requests
import logging
import urllib.parse
from ...config import settings

logger = logging.getLogger("svg_translate")


def get_category_members_api(category, project, limit=500):
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
    except requests.exceptions.RequestException as e:
        logger.error(f"Error: get_category_members : {e}")
    else:
        logger.debug(f"Found {len(pages)} pages in category {category}")

    return pages


def get_category_members_petscan(category, project, limit=500):
    """
    Fetch all pages belonging to a given category from a Wikimedia project using the Petscan API.
    """
    # Build PetScan URL for the given category
    base_url = "https://petscan.wmflabs.org/"

    if category.lower().startswith("category:"):
        category = category[9:]

    params = {
        "language": "commons",
        "project": "wikimedia",
        "categories": f"{category}",
        "format": "plain",
        "depth": 0,
        "ns[10]": 1,
        "doit": "Do it!"
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"

    logger.debug(f"petscan url: {url}")

    headers = {}
    headers["User-Agent"] = settings.oauth.user_agent
    text = ""
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        text = resp.text
    except Exception as e:
        logger.error(f"get_petscan_category_pages: request/json error: {e}")
        return []

    if not text:
        return []

    result = [x.strip() for x in text.splitlines()]

    return result


def get_category_members(category="Category:Pages using gadget owidslider", project="commons.wikimedia.org", limit=500):
    result = get_category_members_api(category, project, limit)

    if not result:
        result = get_category_members_petscan(category, project, limit)

    logger.info(f"Found {len(result)} pages in category {category}")
    return result
