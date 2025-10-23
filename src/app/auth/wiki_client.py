
import os
import mwclient
from typing import Dict

USER_AGENT = os.getenv("USER_AGENT", "Copy SVG Translations/1.0 (https://copy-svg-langs.toolforge.org; tools.copy-svg-langs@toolforge.org)")

UPLOAD_END_POINT = os.getenv("UPLOAD_END_POINT", "commons.wikimedia.org")


def build_site(oauth_credentials: Dict[str, str]) -> mwclient.Site:
    return mwclient.Site(
        UPLOAD_END_POINT,
        path="/w/",
        scheme="https",
        clients_useragent=USER_AGENT,
        consumer_token=oauth_credentials.get("consumer_key"),
        consumer_secret=oauth_credentials.get("consumer_secret"),
        access_token=oauth_credentials.get("access_token"),
        access_secret=oauth_credentials.get("access_secret"),
    )
