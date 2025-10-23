
# Usage

```python
from pathlib import Path
from CopySvgTranslate import start_on_template_title, upload_file

title = "Template:OWID/Parkinsons prevalence"

output_dir = Path(__file__).parent / "svg_data"

result = start_on_template_title(title, output_dir=output_dir, titles_limit=None, overwrite=False)
files = result.get("files", {})

for file_name, file_meta in files.items():
    file_path = file_meta.get("file_path")
    if not file_path:
        continue
    upload_file(file_name, file_path)

```

## MediaWiki OAuth configuration

1. Install dependencies: `pip install -r src/requirements.txt` (or `pip install mwoauth cryptography python-dotenv flask`).
2. Register a MediaWiki OAuth consumer and note the consumer key and secret.
3. Create a `.env` file (or configure your deployment environment) with at least:
   ```bash
   FLASK_SECRET_KEY=change_me_strong_random
   OAUTH_MWURI=https://meta.wikimedia.org/w/index.php
   CONSUMER_KEY=your_consumer_key
   CONSUMER_SECRET=your_consumer_secret
   OAUTH_ENCRYPTION_KEY=generated_32_urlsafe_base64_bytes
   UID_COOKIE_NAME=uid_enc
   UID_COOKIE_MAX_AGE=2592000  # 30 days
   SESSION_COOKIE_SECURE=True
   SESSION_COOKIE_HTTPONLY=True
   SESSION_COOKIE_SAMESITE=Lax
   ```
4. Ensure HTTPS is enabled in production so the secure cookies issued by the app are respected.
5. Apply the database migration to add the `user_tokens` table:
   ```sql
   CREATE TABLE IF NOT EXISTS user_tokens (
     user_id BIGINT PRIMARY KEY,
     username VARCHAR(255) NOT NULL,
     access_token_enc VARBINARY(2048) NOT NULL,
     access_secret_enc VARBINARY(2048) NOT NULL,
     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
     last_used_at TIMESTAMP NULL,
     rotated_at TIMESTAMP NULL
   );
   CREATE INDEX IF NOT EXISTS idx_user_tokens_username ON user_tokens(username);
   ```

With these settings in place the Flask app will present `/login`, `/callback`, and `/logout` endpoints, store encrypted OAuth credentials per user, and surface the signed-in username in the navigation bar. The application also issues signed identification cookies and rate limits repeated login or callback attempts to reduce abuse.
