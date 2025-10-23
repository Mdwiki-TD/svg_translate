# OAuth Configuration Guide

The SVG Translate web interface now relies exclusively on OAuth to obtain
permissions to upload files on behalf of Toolforge users.  This document walks
through the environment variables, secrets, and operational steps required to
run the application locally or in production.

## Required environment variables

Set the following variables before starting the Flask application.  The
deployment tooling should inject the same variables into the runtime
environment (for example, via Toolforge secrets or Kubernetes ConfigMaps).

| Variable | Description |
| --- | --- |
| `OAUTH_MWURI` | Base MediaWiki URI for OAuth handshakes (e.g. `https://commons.wikimedia.org/w/index.php`). |
| `OAUTH_CONSUMER_KEY` | OAuth consumer key issued by MediaWiki. |
| `OAUTH_CONSUMER_SECRET` | OAuth consumer secret issued alongside the key. |
| `OAUTH_ENCRYPTION_KEY` | Fernet key (URL-safe base64 encoded) used to encrypt access tokens at rest. |
| `FLASK_SECRET_KEY` | Secret key used by Flask and the cookie serializer. |

> ⚠️ The value of `OAUTH_ENCRYPTION_KEY` must be a valid Fernet key.  Generate
> one with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
> The application refuses to start if this key is missing or malformed.

## Cookie and session handling

* OAuth handshakes include an explicit callback URL (`/callback`) and a random
  state parameter stored in the session.  The callback validates both the state
  and the request token before persisting credentials.
* Successful logins create an encrypted cookie (`svg_translate_user`) that
  contains only the user identifier.  Tokens remain encrypted in the database.
* Tampered or expired cookies are rejected and cleared automatically.

## Running the login flow locally

1. Register an OAuth consumer on Meta-Wiki with callback URL
   `http://localhost:5000/callback` (or your development origin).
2. Export the environment variables listed above and start the Flask app via
   `python -m flask --app src.app run`.
3. Visit `http://localhost:5000/login`, authorise the application, and verify
   that the navbar shows your username.
4. Submit a translation task.  The background worker receives only the
   consumer/access token tuple for the authenticated user.

## Credential retention and maintenance

* OAuth credentials are retained for 90 days after their last use.  Revoked
  credentials (`rotated_at` set) are eligible for immediate deletion.
* Operators can remove stale entries via the Flask CLI command
  `flask purge-oauth-tokens --max-age-days 90`.  Schedule this command (for
  example, through cron) to keep the credential store tidy.

## Troubleshooting

* **Invalid encryption key** – ensure `OAUTH_ENCRYPTION_KEY` matches the Fernet
  format (44 character, URL-safe base64).  Regenerate the key if unsure.
* **Uploads fail with `missing-oauth`** – confirm the store has a valid access
  token/secret and that both consumer credentials are configured.
* **Cookie instantly disappears** – check the server logs for warnings about a
  bad signature.  This indicates the cookie was tampered with or the Flask
  secret key changed between requests.

For further details, review `src/web/auth.py` and `src/web/db/user_store.py`
which implement the login lifecycle and encrypted credential storage.
