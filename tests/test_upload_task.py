"""Tests for the upload task helpers."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from cryptography.fernet import Fernet
import pytest

from src.app.upload_tasks import start_upload, upload_task


class TestStartUpload:
    def _test_start_upload_success(self):
        pass
