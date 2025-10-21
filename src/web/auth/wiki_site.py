"""

https://chatgpt.com/c/68f74419-c23c-832a-bb77-3a825c71c0eb

"""
import requests
from pathlib import Path
import logging
import os

from requests_oauthlib import OAuth1


logger = logging.getLogger(__name__)

USER_AGENT = os.getenv("USER_AGENT", "Copy SVG Translations/1.0 (https://copy-svg-langs.toolforge.org; tools.copy-svg-langs@toolforge.org)")

UPLOAD_END_POINT = os.getenv("UPLOAD_END_POINT", "commons.wikimedia.org")


class InsufficientPermission(Exception):
    pass


class FileExists(Exception):
    """
    Raised when trying to upload a file that already exists.

    See also: https://www.mediawiki.org/wiki/API:Upload#Upload_warnings
    """

    def __init__(self, file_name: str):
        self.file_name = file_name

    def __str__(self):
        return ('The file "{0}" already exists. Set ignore=True to overwrite it.'
                .format(self.file_name))


class Site:
    """
    Minimal MediaWiki OAuth1 client for Commons uploads.

    - Uses OAuth1 (consumer + access tokens).
    - Provides:
        * page(title): return {"exists": bool, "title": str, "pageid": int|None}
        * upload(file, filename, comment, ignore=True): upload file with CSRF
    """

    def __init__(self, consumer_token, consumer_secret, access_token, access_secret):
        self.consumer_token = consumer_token
        self.consumer_secret = consumer_secret
        self.access_token = access_token
        self.access_secret = access_secret

        self.api = f"https://{UPLOAD_END_POINT}/w/api.php"
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": USER_AGENT})
        self._session.auth = OAuth1(
            client_key=self.consumer_token,
            client_secret=self.consumer_secret,
            resource_owner_key=self.access_token,
            resource_owner_secret=self.access_secret,
            signature_type="auth_header",
        )
        self._csrf_token = None

    def _csrf(self) -> str:
        """Fetch and cache a CSRF token."""
        if self._csrf_token:
            return self._csrf_token

        params = {
            "action": "query",
            "meta": "tokens",
            "type": "csrf",
            "format": "json",
        }
        r = self._session.get(self.api, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        token = data.get("query", {}).get("tokens", {}).get("csrftoken")
        if not token:
            raise InsufficientPermission()
        self._csrf_token = token
        return token

    def page(self, title: str) -> dict:
        """Return minimal page info and existence flag."""
        params = {
            "action": "query",
            "titles": title,
            "prop": "info",
            "format": "json",
        }
        r = self._session.get(self.api, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()

        pages = data.get("query", {}).get("pages", {})
        if not pages:
            return {"exists": False, "title": title, "pageid": None}

        page_obj = next(iter(pages.values()))
        exists = "missing" not in page_obj
        return {
            "exists": exists,
            "title": page_obj.get("title", title),
            "pageid": None if not exists else int(page_obj.get("pageid", 0) or 0),
        }

    def upload(self, file, filename: str, comment: str, ignore: bool = True):
        """
        Upload a file to Commons.

        Parameters:
            file: file-like object opened in binary mode.
            filename (str): Destination filename at Commons without "File:" prefix.
            comment (str): Upload summary.
            ignore (bool): If True, pass ignorewarnings=1 to overwrite or bypass warnings.

        Returns:
            dict on success (API response). Raises on fatal conditions.
        """
        token = self._csrf()

        files = {
            "file": (filename, file, "image/svg+xml"),
        }
        data = {
            "action": "upload",
            "filename": filename,
            "format": "json",
            "token": token,
            "comment": comment or "",
        }
        if ignore:
            data["ignorewarnings"] = 1

        # Use POST multipart for uploads
        r = self._session.post(self.api, data=data, files=files, timeout=120)
        r.raise_for_status()
        resp = r.json()

        # Handle standard API error envelope
        if "error" in resp:
            code = resp["error"].get("code", "")
            info = resp["error"].get("info", "")
            # Rate limit surface for caller
            if code in {"ratelimited", "throttled"} or "rate" in code:
                raise Exception("ratelimited: " + info)
            # Permission issues
            if code in {"permissiondenied", "badtoken", "mwoauth-invalid-authorization"}:
                raise InsufficientPermission()
            raise Exception(f"upload error: {code}: {info}")

        upload = resp.get("upload", {})
        result = upload.get("result")

        # Warnings handling
        warnings = upload.get("warnings", {})
        if warnings and not ignore:
            if "exists" in warnings or "duplicate" in warnings:
                raise FileExists(filename)

        # Success
        if result == "Success":
            return resp

        # Non-success without explicit error
        # Check common warning-only paths when ignore=True
        if result in {"Warning", None} and ignore:
            return resp

        # Fallback: raise a generic error with payload
        raise Exception(f"Unexpected upload response: {resp}")
