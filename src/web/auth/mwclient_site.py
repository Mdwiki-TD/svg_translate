
import os
import mwclient

from mwclient.auth import OAuthAuthentication

USER_AGENT = os.getenv("USER_AGENT", "Copy SVG Translations/1.0 (https://copy-svg-langs.toolforge.org; tools.copy-svg-langs@toolforge.org)")

def make_site(oauth_credentials):

    oauth = OAuthAuthentication(
        oauth_credentials.get("consumer_key"),
        oauth_credentials.get("consumer_secret"),
        oauth_credentials.get("access_token"),
        oauth_credentials.get("access_secret"),
    )

    site = mwclient.Site(
        ("https", "commons.wikimedia.org"),
        clients_useragent=USER_AGENT,
        path="/w/",
        auth=oauth,
    )

    return site
