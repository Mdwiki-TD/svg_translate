"""Tests for the upload task helpers."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from cryptography.fernet import Fernet
import pytest

os.environ.setdefault("FERNET_KEY", Fernet.generate_key().decode("utf-8"))
os.environ.setdefault("CONSUMER_KEY", "test-consumer-key")
os.environ.setdefault("CONSUMER_SECRET", "test-consumer-secret")
os.environ.setdefault("OAUTH_MWURI", "https://example.org/w/index.php")

from src.web.upload_task import _safe_invoke_callback, start_upload, upload_task


@pytest.fixture
def sample_files_to_upload():
    return {
        "File1.svg": {"file_path": "File1.svg", "new_languages": "ar, fr"},
        "File2.svg": {"file_path": "File2.svg", "new_languages": "de, it"},
    }


class TestSafeInvokeCallback:
    def test_callback_is_none_no_error(self):
        _safe_invoke_callback(None, 1, 10, Path("test.svg"), "success")

    def test_callback_is_called(self):
        callback = MagicMock()
        path = Path("test.svg")

        _safe_invoke_callback(callback, 5, 10, path, "success")

        callback.assert_called_once_with(5, 10, path, "success")

    def test_callback_exception_is_caught(self):
        callback = MagicMock(side_effect=RuntimeError("Callback error"))

        _safe_invoke_callback(callback, 1, 10, Path("test.svg"), "failed")


class TestStartUpload:
    def test_start_upload_success(self):
        site = MagicMock()
        site.logged_in = True
        site.username = "test_user"

        with patch("src.web.upload_task.upload_file", return_value={"result": "Success"}):
            with patch("src.web.upload_task.tqdm", lambda items, **_: items):
                result = start_upload(
                    {"File1.svg": {"file_path": "File1.svg", "new_languages": "ar, fr"}},
                    "[[:File:Main.svg]]",
                    site,
                )

        assert result["done"] == 1
        assert result["not_done"] == 0
        assert result["errors"] == []

    def test_start_upload_failure_collects_errors(self):
        site = MagicMock()

        with patch(
            "src.web.upload_task.upload_file",
            return_value={"result": "Failure", "error": "Permission denied"},
        ):
            with patch("src.web.upload_task.tqdm", lambda items, **_: items):
                result = start_upload(
                    {"File1.svg": {"file_path": "File1.svg"}},
                    "[[:File:Main.svg]]",
                    site,
                )

        assert result["done"] == 0
        assert result["not_done"] == 1
        assert result["errors"] == ["Permission denied"]

    def test_start_upload_invokes_callback(self):
        site = MagicMock()
        callback = MagicMock()

        with patch("src.web.upload_task.upload_file", return_value={"result": "Success"}):
            with patch("src.web.upload_task.tqdm", lambda items, **_: items):
                start_upload(
                    {
                        "File1.svg": {"file_path": "File1.svg", "new_languages": "ar, fr"},
                        "File2.svg": {"file_path": "File2.svg"},
                    },
                    "[[:File:Main.svg]]",
                    site,
                    per_file_callback=callback,
                )

        assert callback.call_count == 2


class TestUploadTask:
    @patch("src.web.upload_task.build_oauth_site")
    @patch("src.web.upload_task.start_upload")
    def test_upload_task_success(self, mock_start_upload, mock_build_site, sample_files_to_upload):
        mock_start_upload.return_value = {"done": 2, "not_done": 0, "errors": []}
        mock_build_site.return_value = MagicMock()

        stages = {"status": "Pending", "message": ""}
        result, updated_stages = upload_task(
            stages,
            sample_files_to_upload,
            "Main.svg",
            do_upload=True,
            user={"token_enc": "token", "username": "user"},
        )

        assert result["done"] == 2
        assert updated_stages["status"] == "Completed"
        mock_build_site.assert_called_once()
        mock_start_upload.assert_called_once()

    def test_upload_task_missing_token(self, sample_files_to_upload):
        stages = {"status": "Pending", "message": ""}
        result, updated_stages = upload_task(
            stages,
            sample_files_to_upload,
            "Main.svg",
            do_upload=True,
            user={},
        )

        assert result["skipped"] is True
        assert result["reason"] == "missing-token"
        assert updated_stages["status"] == "Failed"

    @patch("src.web.upload_task.build_oauth_site", side_effect=RuntimeError("boom"))
    def test_upload_task_oauth_failure(self, mock_build_site, sample_files_to_upload):
        stages = {"status": "Pending", "message": ""}
        result, updated_stages = upload_task(
            stages,
            sample_files_to_upload,
            "Main.svg",
            do_upload=True,
            user={"token_enc": "token"},
        )

        assert result["skipped"] is True
        assert result["reason"] == "oauth-auth-failed"
        assert updated_stages["status"] == "Failed"
        mock_build_site.assert_called_once()

    @patch("src.web.upload_task.build_oauth_site")
    @patch("src.web.upload_task.start_upload")
    def test_upload_task_updates_message(self, mock_start_upload, mock_build_site, sample_files_to_upload):
        mock_start_upload.return_value = {"done": 1, "not_done": 1, "errors": ["x"]}
        mock_build_site.return_value = MagicMock()

        stages = {"status": "Pending", "message": ""}
        result, updated_stages = upload_task(
            stages,
            sample_files_to_upload,
            "Main.svg",
            do_upload=True,
            user={"token_enc": "token"},
        )

        assert result["not_done"] == 1
        assert updated_stages["status"] == "Failed"
        assert "Files uploaded" in updated_stages["message"]

    def test_upload_task_disabled(self, sample_files_to_upload):
        stages = {"status": "Pending", "message": ""}
        result, updated_stages = upload_task(
            stages,
            sample_files_to_upload,
            "Main.svg",
            do_upload=False,
            user={"token_enc": "token"},
        )

        assert result["skipped"] is True
        assert updated_stages["status"] == "Skipped"
        assert "disabled" in updated_stages["message"].lower()
