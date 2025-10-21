"""Tests for OAuth-enabled upload helpers."""

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


if "mwclient" not in sys.modules:
    mwclient_stub = types.ModuleType("mwclient")
    errors_stub = types.ModuleType("mwclient.errors")
    errors_stub.LoginError = Exception
    mwclient_stub.errors = types.SimpleNamespace(LoginError=Exception)
    mwclient_stub.Site = MagicMock
    sys.modules["mwclient.errors"] = errors_stub
    sys.modules["mwclient"] = mwclient_stub

if "tqdm" not in sys.modules:
    tqdm_stub = types.ModuleType("tqdm")
    tqdm_stub.tqdm = lambda iterable=None, **_: iterable if iterable else []
    sys.modules["tqdm"] = tqdm_stub


from src.web.upload_task import (  # noqa: E402  # isort:skip
    _safe_invoke_callback,
    start_upload,
    upload_task,
)


@pytest.fixture
def sample_files_to_upload() -> dict:
    return {
        "File1.svg": {"file_path": "File1.svg", "new_languages": "ar, fr"},
        "File2.svg": {"file_path": "File2.svg", "new_languages": "de"},
    }


@pytest.fixture
def oauth_credentials() -> dict:
    return {
        "consumer_key": "ck",
        "consumer_secret": "cs",
        "access_token": "atk",
        "access_secret": "ats",
    }


class TestSafeInvokeCallback:
    def test_callback_is_none_no_error(self) -> None:
        _safe_invoke_callback(None, 1, 2, Path("dummy"), "success")

    def test_callback_invoked(self) -> None:
        callback = MagicMock()
        target_path = Path("dummy")
        _safe_invoke_callback(callback, 1, 2, target_path, "success")
        callback.assert_called_once_with(1, 2, target_path, "success")

    def test_callback_exception_is_caught(self) -> None:
        callback = MagicMock(side_effect=RuntimeError("boom"))
        _safe_invoke_callback(callback, 1, 1, Path("dummy"), "failed")


class TestStartUpload:
    @patch("src.web.upload_task.upload_file")
    @patch("src.web.upload_task.mwclient.Site")
    @patch("src.web.upload_task.OAuthAuthentication")
    def test_successful_upload_flow(
        self,
        mock_auth,
        mock_site_cls,
        mock_upload_file,
        sample_files_to_upload,
        oauth_credentials,
    ) -> None:
        site = MagicMock()
        mock_site_cls.return_value = site
        mock_upload_file.return_value = {"result": "Success"}

        result = start_upload(sample_files_to_upload, "[[:File:Main.svg]]", oauth_credentials)

        mock_auth.assert_called_once_with("ck", "cs", "atk", "ats")
        mock_site_cls.assert_called_once()
        assert result == {"done": 2, "not_done": 0, "errors": []}

    @patch("src.web.upload_task.upload_file")
    @patch("src.web.upload_task.mwclient.Site")
    @patch("src.web.upload_task.OAuthAuthentication")
    def test_upload_collects_errors(
        self,
        mock_auth,
        mock_site_cls,
        mock_upload_file,
        oauth_credentials,
    ) -> None:
        site = MagicMock()
        mock_site_cls.return_value = site
        mock_upload_file.return_value = {"result": "Failure", "error": "Permission"}

        result = start_upload({"File.svg": {"file_path": "File.svg"}}, "[[:File:Main.svg]]", oauth_credentials)

        assert result["done"] == 0
        assert result["not_done"] == 1
        assert result["errors"] == ["Permission"]

    @patch("src.web.upload_task.OAuthAuthentication", None)
    def test_start_upload_without_oauth_support(self, oauth_credentials) -> None:
        with pytest.raises(RuntimeError):
            start_upload({}, "[[:File:Main.svg]]", oauth_credentials)


class TestUploadTask:
    @patch("src.web.upload_task.start_upload")
    def test_missing_oauth_credentials(self, mock_start_upload, sample_files_to_upload) -> None:
        stages = {"status": "Pending", "message": "Uploading"}
        result, updated = upload_task(stages, sample_files_to_upload, "Main.svg", do_upload=True, oauth_credentials={})

        assert result["reason"] == "missing-oauth"
        assert updated["status"] == "Failed"
        mock_start_upload.assert_not_called()

    @patch("src.web.upload_task.start_upload")
    def test_delegates_to_start_upload(
        self,
        mock_start_upload,
        sample_files_to_upload,
        oauth_credentials,
    ) -> None:
        mock_start_upload.return_value = {"done": 1, "not_done": 0, "errors": []}

        stages = {"status": "Pending", "message": "Uploading"}
        result, updated = upload_task(
            stages,
            sample_files_to_upload,
            "Main.svg",
            do_upload=True,
            oauth_credentials=oauth_credentials,
        )

        mock_start_upload.assert_called_once()
        assert result["done"] == 1
        assert updated["status"] == "Completed"
