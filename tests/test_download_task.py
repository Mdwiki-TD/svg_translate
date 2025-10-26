"""
Comprehensive unit tests for download_task module.
Tests cover download functionality, and error handling.
"""
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, call

import pytest

# Mock modules before imports
if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")
    exceptions_stub = types.ModuleType("requests.exceptions")
    exceptions_stub.RequestException = Exception
    requests_stub.exceptions = types.SimpleNamespace(RequestException=Exception)
    requests_stub.Session = Mock
    sys.modules["requests.exceptions"] = exceptions_stub
    sys.modules["requests"] = requests_stub

if "tqdm" not in sys.modules:
    tqdm_stub = types.ModuleModule("tqdm")
    tqdm_stub.tqdm = lambda iterable=None, **_: iterable if iterable else []
    sys.modules["tqdm"] = tqdm_stub

from src.app.download_tasks.download import (
    download_commons_svgs,
    download_task,
)


@pytest.fixture
def mock_requests_session():
    """Create a mock requests session."""
    session = MagicMock()
    response = MagicMock()
    response.status_code = 200
    response.content = b"<svg>test</svg>"
    session.get.return_value = response
    return session


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


class TestDownloadCommonsSvgs:
    """Test download_commons_svgs function."""

    @patch("src.app.download_tasks.download.requests.Session")
    def test_download_single_file(self, mock_session_class, temp_output_dir):
        """Test downloading a single SVG file."""
        session = MagicMock()
        response = MagicMock()
        response.status_code = 200
        response.content = b"<svg>content</svg>"
        session.get.return_value = response
        mock_session_class.return_value = session

        titles = ["Example.svg"]
        result = download_commons_svgs(titles, temp_output_dir)

        assert len(result) == 1
        assert (temp_output_dir / "Example.svg").exists()

    @patch("src.app.download_tasks.download.requests.Session")
    def test_download_multiple_files(self, mock_session_class, temp_output_dir):
        """Test downloading multiple SVG files."""
        session = MagicMock()
        response = MagicMock()
        response.status_code = 200
        response.content = b"<svg>content</svg>"
        session.get.return_value = response
        mock_session_class.return_value = session

        titles = ["File1.svg", "File2.svg", "File3.svg"]
        result = download_commons_svgs(titles, temp_output_dir)

        assert len(result) == 3
        for title in titles:
            assert (temp_output_dir / title).exists()

    @patch("src.app.download_tasks.download.requests.Session")
    def test_download_skips_existing_files(self, mock_session_class, temp_output_dir):
        """Test that existing files are skipped."""
        session = MagicMock()
        mock_session_class.return_value = session

        # Create existing file
        existing_file = temp_output_dir / "Existing.svg"
        existing_file.write_bytes(b"<svg>old content</svg>")

        titles = ["Existing.svg"]
        result = download_commons_svgs(titles, temp_output_dir)

        # Should not download, file already exists
        session.get.assert_not_called()
        assert len(result) == 1
        # Content should remain unchanged
        assert existing_file.read_bytes() == b"<svg>old content</svg>"

    @patch("src.app.download_tasks.download.requests.Session")
    def test_download_handles_network_error(self, mock_session_class, temp_output_dir):
        """Test handling of network errors."""
        import requests
        session = MagicMock()
        session.get.side_effect = requests.exceptions.RequestException("Network error")
        mock_session_class.return_value = session

        titles = ["NetworkError.svg"]
        result = download_commons_svgs(titles, temp_output_dir)

        # Should return empty list for failed downloads
        assert len(result) == 0

    @patch("src.app.download_tasks.download.requests.Session")
    def test_download_handles_404_error(self, mock_session_class, temp_output_dir):
        """Test handling of 404 not found errors."""
        session = MagicMock()
        response = MagicMock()
        response.status_code = 404
        session.get.return_value = response
        mock_session_class.return_value = session

        titles = ["NotFound.svg"]
        result = download_commons_svgs(titles, temp_output_dir)

        # File should not be in result
        assert len(result) == 0

    @patch("src.app.download_tasks.download.requests.Session")
    def test_download_sets_user_agent(self, mock_session_class, temp_output_dir):
        """Test that User-Agent header is set."""
        session = MagicMock()
        response = MagicMock()
        response.status_code = 200
        response.content = b"<svg>content</svg>"
        session.get.return_value = response
        mock_session_class.return_value = session

        titles = ["Test.svg"]
        download_commons_svgs(titles, temp_output_dir)

        # Check that headers were updated
        session.headers.update.assert_called_once()
        call_args = session.headers.update.call_args[0][0]
        assert "User-Agent" in call_args

    @patch("src.app.download_tasks.download.requests.Session")
    def test_download_empty_list(self, mock_session_class, temp_output_dir):
        """Test downloading with empty titles list."""
        session = MagicMock()
        mock_session_class.return_value = session

        result = download_commons_svgs([], temp_output_dir)

        assert len(result) == 0
        session.get.assert_not_called()


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @patch("src.app.download_tasks.download.requests.Session")
    def test_download_with_special_characters_in_filename(self, mock_session_class, temp_output_dir):
        """Test downloading files with special characters in names."""
        session = MagicMock()
        response = MagicMock()
        response.status_code = 200
        response.content = b"<svg>content</svg>"
        session.get.return_value = response
        mock_session_class.return_value = session

        titles = ["File with spaces.svg", "File-with-dashes.svg"]
        result = download_commons_svgs(titles, temp_output_dir)

        assert len(result) == 2

    @patch("src.app.download_tasks.download.requests.Session")
    def test_download_with_unicode_filename(self, mock_session_class, temp_output_dir):
        """Test downloading files with unicode characters in names."""
        session = MagicMock()
        response = MagicMock()
        response.status_code = 200
        response.content = b"<svg>content</svg>"
        session.get.return_value = response
        mock_session_class.return_value = session

        titles = ["文件.svg", "Файл.svg"]
        result = download_commons_svgs(titles, temp_output_dir)

        assert len(result) == 2

    @patch("src.app.download_tasks.download.requests.Session")
    def test_download_timeout_handling(self, mock_session_class, temp_output_dir):
        """Test handling of request timeouts."""
        import requests
        session = MagicMock()
        session.get.side_effect = requests.exceptions.RequestException("Timeout")
        mock_session_class.return_value = session

        titles = ["Timeout.svg"]
        result = download_commons_svgs(titles, temp_output_dir)

        assert len(result) == 0
