"""Tests for the upload task helpers."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from cryptography.fernet import Fernet
import pytest

os.environ.setdefault("FLASK_SECRET_KEY", "test-secret")
os.environ.setdefault("OAUTH_ENCRYPTION_KEY", Fernet.generate_key().decode("utf-8"))
os.environ.setdefault("OAUTH_CONSUMER_KEY", "test-consumer-key")
os.environ.setdefault("OAUTH_CONSUMER_SECRET", "test-consumer-secret")
os.environ.setdefault("OAUTH_MWURI", "https://example.org/w/index.php")

from src.app.web.upload_task import start_upload, upload_task


class TestStartUpload:
    def _test_start_upload_success(self):
        pass
