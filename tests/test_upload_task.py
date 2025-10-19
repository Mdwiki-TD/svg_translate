"""
Comprehensive unit tests for upload_task module.
Tests cover upload functionality, authentication, progress callbacks, and error handling.
"""
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, call

import pytest

# Mock modules before imports
if "mwclient" not in sys.modules:
    mwclient_stub = types.ModuleType("mwclient")
    errors_stub = types.ModuleType("mwclient.errors")
    errors_stub.LoginError = Exception
    mwclient_stub.errors = types.SimpleNamespace(LoginError=Exception)
    mwclient_stub.Site = Mock
    sys.modules["mwclient.errors"] = errors_stub
    sys.modules["mwclient"] = mwclient_stub

if "tqdm" not in sys.modules:
    tqdm_stub = types.ModuleType("tqdm")
    tqdm_stub.tqdm = lambda iterable=None, **_: iterable if iterable else []
    sys.modules["tqdm"] = tqdm_stub

# Mock user_info before importing upload_task
user_info_stub = types.ModuleType("user_info")
user_info_stub.username = "test_user"
user_info_stub.password = ""
sys.modules["user_info"] = user_info_stub

from src.web.upload_task import (
    start_upload,
    upload_task,
    _safe_invoke_callback,
)


@pytest.fixture
def mock_site():
    """Create a mock mwclient Site."""
    site = MagicMock()
    site.logged_in = True
    site.username = "test_user"
    site.login = MagicMock()
    return site


@pytest.fixture
def sample_files_to_upload():
    """Create sample files data for upload."""
    return {
        "File1.svg": {
            "file_path": "File1.svg",
            "new_languages": "ar, fr, es",
        },
        "File2.svg": {
            "file_path": "File2.svg",
            "new_languages": "de, it",
        },
    }


class TestSafeInvokeCallback:
    """Test _safe_invoke_callback helper function."""
    
    def test_callback_is_none_no_error(self):
        """Test that None callback doesn't raise error."""
        # Should not raise
        _safe_invoke_callback(None, 1, 10, Path("test.svg"), "success")
    
    def test_callback_is_called(self):
        """Test that callback is invoked with correct arguments."""
        callback = MagicMock()
        path = Path("test.svg")
        
        _safe_invoke_callback(callback, 5, 10, path, "success")
        
        callback.assert_called_once_with(5, 10, path, "success")
    
    def test_callback_exception_is_caught(self):
        """Test that callback exceptions are caught and logged."""
        callback = MagicMock(side_effect=Exception("Callback error"))
        
        # Should not raise, exception is caught
        _safe_invoke_callback(callback, 1, 10, Path("test.svg"), "failed")


class TestStartUpload:
    """Test start_upload function."""
    
    @patch("src.web.upload_task.mwclient.Site")
    @patch("src.web.upload_task.upload_file")
    def test_upload_single_file_success(self, mock_upload_file, mock_site_class, sample_files_to_upload):
        """Test uploading a single file successfully."""
        site = MagicMock()
        site.logged_in = True
        site.username = "test_user"
        mock_site_class.return_value = site
        
        mock_upload_file.return_value = {"result": "Success"}
        
        files = {"File1.svg": sample_files_to_upload["File1.svg"]}
        result = start_upload(files, "[[:File:Main.svg]]", "user", "pass")
        
        assert result["done"] == 1
        assert result["not_done"] == 0
        assert len(result["errors"]) == 0
    
    @patch("src.web.upload_task.mwclient.Site")
    @patch("src.web.upload_task.upload_file")
    def test_upload_multiple_files_success(self, mock_upload_file, mock_site_class, sample_files_to_upload):
        """Test uploading multiple files successfully."""
        site = MagicMock()
        site.logged_in = True
        mock_site_class.return_value = site
        
        mock_upload_file.return_value = {"result": "Success"}
        
        result = start_upload(sample_files_to_upload, "[[:File:Main.svg]]", "user", "pass")
        
        assert result["done"] == 2
        assert result["not_done"] == 0
    
    @patch("src.web.upload_task.mwclient.Site")
    @patch("src.web.upload_task.upload_file")
    def test_upload_file_failure(self, mock_upload_file, mock_site_class, sample_files_to_upload):
        """Test handling upload failures."""
        site = MagicMock()
        site.logged_in = True
        mock_site_class.return_value = site
        
        mock_upload_file.return_value = {"result": "Failure", "error": "Permission denied"}
        
        files = {"File1.svg": sample_files_to_upload["File1.svg"]}
        result = start_upload(files, "[[:File:Main.svg]]", "user", "pass")
        
        assert result["done"] == 0
        assert result["not_done"] == 1
        assert len(result["errors"]) == 1
        assert result["errors"][0] == "Permission denied"
    
    @patch("src.web.upload_task.mwclient.Site")
    @patch("src.web.upload_task.upload_file")
    def test_upload_with_callback(self, mock_upload_file, mock_site_class, sample_files_to_upload):
        """Test upload with progress callback."""
        site = MagicMock()
        site.logged_in = True
        mock_site_class.return_value = site
        
        mock_upload_file.return_value = {"result": "Success"}
        callback = MagicMock()
        
        start_upload(sample_files_to_upload, "[[:File:Main.svg]]", "user", "pass", per_file_callback=callback)
        
        # Callback should be called for each file
        assert callback.call_count == 2
    
    @patch("src.web.upload_task.mwclient.Site")
    def test_upload_login_required(self, mock_site_class, sample_files_to_upload):
        """Test that login is attempted."""
        site = MagicMock()
        site.logged_in = False
        mock_site_class.return_value = site
        
        start_upload(sample_files_to_upload, "[[:File:Main.svg]]", "user", "pass")
        
        site.login.assert_called_once_with("user", "pass")
    
    @patch("src.web.upload_task.mwclient.Site")
    @patch("src.web.upload_task.upload_file")
    def test_upload_mixed_results(self, mock_upload_file, mock_site_class):
        """Test upload with mixed success and failure."""
        site = MagicMock()
        site.logged_in = True
        mock_site_class.return_value = site
        
        # First file succeeds, second fails
        mock_upload_file.side_effect = [
            {"result": "Success"},
            {"result": "Failure", "error": "File exists"},
        ]
        
        files = {
            "File1.svg": {"file_path": "File1.svg"},
            "File2.svg": {"file_path": "File2.svg"},
        }
        result = start_upload(files, "[[:File:Main.svg]]", "user", "pass")
        
        assert result["done"] == 1
        assert result["not_done"] == 1
        assert len(result["errors"]) == 1
    
    @patch("src.web.upload_task.mwclient.Site")
    @patch("src.web.upload_task.upload_file")
    def test_upload_creates_proper_summary(self, mock_upload_file, mock_site_class):
        """Test that upload summary is created correctly."""
        site = MagicMock()
        site.logged_in = True
        mock_site_class.return_value = site
        
        mock_upload_file.return_value = {"result": "Success"}
        
        files = {
            "File1.svg": {
                "file_path": "File1.svg",
                "new_languages": "ar, fr",
            },
        }
        start_upload(files, "[[:File:Main.svg]]", "user", "pass")
        
        # Check that upload_file was called with proper summary
        call_args = mock_upload_file.call_args
        summary = call_args[1]["summary"] if "summary" in call_args[1] else call_args[0][5]
        assert "ar, fr" in summary
        assert "[[:File:Main.svg]]" in summary
    
    @patch("src.web.upload_task.mwclient.Site")
    @patch("src.web.upload_task.upload_file")
    def test_upload_without_new_languages(self, mock_upload_file, mock_site_class):
        """Test upload with file missing new_languages field."""
        site = MagicMock()
        site.logged_in = True
        mock_site_class.return_value = site
        
        mock_upload_file.return_value = {"result": "Success"}
        
        files = {"File1.svg": {"file_path": "File1.svg"}}
        result = start_upload(files, "[[:File:Main.svg]]", "user", "pass")
        
        assert result["done"] == 1


class TestUploadTask:
    """Test upload_task wrapper function."""
    
    @patch("src.web.upload_task.start_upload")
    @patch("src.web.upload_task.username", "test_user")
    @patch("src.web.upload_task.password", "test_pass")
    def test_upload_task_success(self, mock_start_upload, sample_files_to_upload):
        """Test successful upload task."""
        mock_start_upload.return_value = {"done": 2, "not_done": 0, "errors": []}
        
        stages = {"status": "Pending", "message": ""}
        result, updated_stages = upload_task(
            stages,
            sample_files_to_upload,
            "Main.svg",
            do_upload=True
        )
        
        assert result["done"] == 2
        assert updated_stages["status"] == "Completed"
    
    @patch("src.web.upload_task.start_upload")
    @patch("src.web.upload_task.username", "test_user")
    @patch("src.web.upload_task.password", "test_pass")
    def test_upload_task_with_failures(self, mock_start_upload, sample_files_to_upload):
        """Test upload task with some failures."""
        mock_start_upload.return_value = {"done": 1, "not_done": 1, "errors": ["Error"]}
        
        stages = {"status": "Pending", "message": ""}
        result, updated_stages = upload_task(
            stages,
            sample_files_to_upload,
            "Main.svg",
            do_upload=True
        )
        
        assert result["not_done"] == 1
        assert updated_stages["status"] == "Failed"
    
    @patch("src.web.upload_task.username", "test_user")
    @patch("src.web.upload_task.password", "test_pass")
    def test_upload_task_disabled(self, sample_files_to_upload):
        """Test upload task when upload is disabled."""
        stages = {"status": "Pending", "message": ""}
        result, updated_stages = upload_task(
            stages,
            sample_files_to_upload,
            "Main.svg",
            do_upload=False
        )
        
        assert result["skipped"] is True
        assert updated_stages["status"] == "Skipped"
        assert "disabled" in updated_stages["message"].lower()
    
    @patch("src.web.upload_task.username", "test_user")
    @patch("src.web.upload_task.password", "test_pass")
    def test_upload_task_empty_files(self):
        """Test upload task with no files to upload."""
        stages = {"status": "Pending", "message": ""}
        result, updated_stages = upload_task(
            stages,
            {},
            "Main.svg",
            do_upload=True
        )
        
        assert result["skipped"] is True
        assert updated_stages["status"] == "Skipped"
        assert "no files" in updated_stages["message"].lower()
    
    @patch("src.web.upload_task.username", None)
    @patch("src.web.upload_task.password", None)
    def test_upload_task_missing_credentials(self, sample_files_to_upload):
        """Test upload task with missing credentials."""
        stages = {"status": "Pending", "message": ""}
        result, updated_stages = upload_task(
            stages,
            sample_files_to_upload,
            "Main.svg",
            do_upload=True
        )
        
        assert result["skipped"] is True
        assert result["reason"] == "missing-creds"
        assert updated_stages["status"] == "Failed"
    
    @patch("src.web.upload_task.start_upload")
    @patch("src.web.upload_task.username", "test_user")
    @patch("src.web.upload_task.password", "test_pass")
    def test_upload_task_with_progress_updater(self, mock_start_upload, sample_files_to_upload):
        """Test upload task with progress updater."""
        mock_start_upload.return_value = {"done": 2, "not_done": 0, "errors": []}
        
        progress_updater = MagicMock()
        stages = {"status": "Pending", "message": ""}
        
        upload_task(
            stages,
            sample_files_to_upload,
            "Main.svg",
            do_upload=True,
            progress_updater=progress_updater
        )
        
        # Progress updater should be called
        assert progress_updater.called
    
    @patch("src.web.upload_task.start_upload")
    @patch("src.web.upload_task.username", "test_user")
    @patch("src.web.upload_task.password", "test_pass")
    def test_upload_task_progress_updater_exception_caught(self, mock_start_upload, sample_files_to_upload):
        """Test that progress updater exceptions are caught."""
        mock_start_upload.return_value = {"done": 2, "not_done": 0, "errors": []}
        
        progress_updater = MagicMock(side_effect=Exception("Updater error"))
        stages = {"status": "Pending", "message": ""}
        
        # Should not raise exception
        result, _ = upload_task(
            stages,
            sample_files_to_upload,
            "Main.svg",
            do_upload=True,
            progress_updater=progress_updater
        )
        
        assert result["done"] == 2
    
    @patch("src.web.upload_task.start_upload")
    @patch("src.web.upload_task.username", "test_user")
    @patch("src.web.upload_task.password", "test_pass")
    def test_upload_task_updates_message(self, mock_start_upload, sample_files_to_upload):
        """Test that upload task updates stages message."""
        mock_start_upload.return_value = {"done": 2, "not_done": 0, "errors": []}
        
        stages = {"status": "Pending", "message": ""}
        _, updated_stages = upload_task(
            stages,
            sample_files_to_upload,
            "Main.svg",
            do_upload=True
        )
        
        # Message should contain upload statistics
        assert "2" in updated_stages["message"]
        assert "uploaded" in updated_stages["message"].lower()


class TestUploadIntegration:
    """Integration tests for upload functionality."""
    
    @patch("src.web.upload_task.mwclient.Site")
    @patch("src.web.upload_task.upload_file")
    @patch("src.web.upload_task.username", "test_user")
    @patch("src.web.upload_task.password", "test_pass")
    def test_full_upload_workflow(self, mock_upload_file, mock_site_class):
        """Test complete upload workflow."""
        site = MagicMock()
        site.logged_in = True
        site.username = "test_user"
        mock_site_class.return_value = site
        
        mock_upload_file.return_value = {"result": "Success"}
        
        files = {
            "File1.svg": {"file_path": "File1.svg", "new_languages": "ar"},
            "File2.svg": {"file_path": "File2.svg", "new_languages": "fr"},
        }
        stages = {"status": "Pending", "message": ""}
        progress_calls = []
        
        def track_progress():
            progress_calls.append(stages["message"])
        
        result, updated_stages = upload_task(
            stages,
            files,
            "Main.svg",
            do_upload=True,
            progress_updater=track_progress
        )
        
        assert result["done"] == 2
        assert updated_stages["status"] == "Completed"
        assert len(progress_calls) > 0


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    @patch("src.web.upload_task.mwclient.Site")
    @patch("src.web.upload_task.upload_file")
    def test_upload_with_none_file_path(self, mock_upload_file, mock_site_class):
        """Test upload when file_path is None."""
        site = MagicMock()
        site.logged_in = True
        mock_site_class.return_value = site
        
        mock_upload_file.return_value = {"result": "Success"}
        
        files = {"File1.svg": {"new_languages": "ar"}}  # Missing file_path
        result = start_upload(files, "[[:File:Main.svg]]", "user", "pass")
        
        # Should handle gracefully
        assert isinstance(result, dict)
    
    @patch("src.web.upload_task.mwclient.Site")
    @patch("src.web.upload_task.upload_file")
    def test_upload_with_non_dict_file_data(self, mock_upload_file, mock_site_class):
        """Test upload when file data is not a dict."""
        site = MagicMock()
        site.logged_in = True
        mock_site_class.return_value = site
        
        mock_upload_file.return_value = {"result": "Success"}
        
        files = {"File1.svg": "not_a_dict"}
        result = start_upload(files, "[[:File:Main.svg]]", "user", "pass")
        
        # Should handle gracefully
        assert isinstance(result, dict)
    
    @patch("src.web.upload_task.mwclient.Site")
    @patch("src.web.upload_task.upload_file")
    def test_upload_file_returns_none(self, mock_upload_file, mock_site_class):
        """Test when upload_file returns None."""
        site = MagicMock()
        site.logged_in = True
        mock_site_class.return_value = site
        
        mock_upload_file.return_value = None
        
        files = {"File1.svg": {"file_path": "File1.svg"}}
        result = start_upload(files, "[[:File:Main.svg]]", "user", "pass")
        
        # Should handle None result
        assert result["not_done"] == 1
    
    @patch("src.web.upload_task.start_upload")
    @patch("src.web.upload_task.username", "test_user")
    @patch("src.web.upload_task.password", "test_pass")
    def test_upload_task_none_do_upload(self, _mock_start_upload):
        """Test upload_task when do_upload is None (falsy)."""
        stages = {"status": "Pending", "message": ""}
        files = {"File1.svg": {"file_path": "File1.svg"}}
        
        result, updated_stages = upload_task(stages, files, "Main.svg", do_upload=None)
        
        assert result["skipped"] is True
        assert updated_stages["status"] == "Skipped"