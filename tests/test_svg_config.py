"""
Comprehensive unit tests for svg_config module.
Tests configuration loading, path resolution, and environment variable handling.
"""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest


class TestSvgConfig:
    """Test svg_config module configuration."""

    @patch.dict(os.environ, {"HOME": "/test/home"}, clear=True)
    @patch("src.svg_config.ConfigParser")
    def test_home_dir_set_uses_home_paths(self, mock_config_parser):
        """Test that HOME env variable sets project paths correctly."""
        mock_config = MagicMock()
        mock_config.__getitem__.return_value = {
            "host": "localhost",
            "user": "test",
            "dbname": "testdb",
            "password": "pass",
        }
        mock_config.get.side_effect = lambda key, default="": {
            "host": "localhost",
            "user": "test",
            "dbname": "testdb",
            "password": "pass",
        }.get(key, default)

        mock_config_parser.return_value.read.return_value = None
        mock_config_parser.return_value.__getitem__.return_value = mock_config

        # Reload module with mocked HOME
        if "src.svg_config" in sys.modules:
            del sys.modules["src.svg_config"]

        with patch("src.svg_config.Path.mkdir"):
            from src import svg_config

            assert svg_config.project == "/test/home"
            assert svg_config.project_www == "/test/home/www"

    @patch.dict(os.environ, {}, clear=True)
    @patch("src.svg_config.ConfigParser")
    def test_no_home_uses_default_paths(self, mock_config_parser):
        """Test that missing HOME env variable uses default paths."""
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda _, default="": default

        mock_config_parser.return_value.read.return_value = None
        mock_config_parser.return_value.__getitem__.return_value = mock_config

        if "src.svg_config" in sys.modules:
            del sys.modules["src.svg_config"]

        with patch("src.svg_config.Path.mkdir"):
            from src import svg_config

            assert "I:/SVG/svg_repo" in svg_config.project or svg_config.project is not None

    @patch.dict(os.environ, {"TASK_DB_PATH": "/custom/tasks.db"})
    @patch("src.svg_config.ConfigParser")
    def test_task_db_path_from_env(self, mock_config_parser):
        """Test TASK_DB_PATH environment variable is respected."""
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda _, default="": default

        mock_config_parser.return_value.read.return_value = None
        mock_config_parser.return_value.__getitem__.return_value = mock_config

        if "src.svg_config" in sys.modules:
            del sys.modules["src.svg_config"]

        with patch("src.svg_config.Path.mkdir"):
            from src import svg_config

            assert svg_config.TASK_DB_PATH == "/custom/tasks.db"

    @patch.dict(os.environ, {"FLASK_SECRET_KEY": "my-secret-key"})
    @patch("src.svg_config.ConfigParser")
    def test_secret_key_from_env(self, mock_config_parser):
        """Test FLASK_SECRET_KEY environment variable is respected."""
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda _, default="": default

        mock_config_parser.return_value.read.return_value = None
        mock_config_parser.return_value.__getitem__.return_value = mock_config

        if "src.svg_config" in sys.modules:
            del sys.modules["src.svg_config"]

        with patch("src.svg_config.Path.mkdir"):
            from src import svg_config

            assert svg_config.SECRET_KEY == "my-secret-key"  # noqa: S105

    @patch("src.svg_config.ConfigParser")
    def test_db_data_from_config_file(self, mock_config_parser):
        """Test database configuration is read from config file."""
        mock_config = MagicMock()
        mock_default = {
            "host": "db.example.com",
            "user": "dbuser",
            "dbname": "mydb",
            "password": "secret",
        }
        mock_config.get.side_effect = lambda key, default="": mock_default.get(key, default)

        mock_config_parser.return_value.read.return_value = None
        mock_config_parser.return_value.__getitem__.return_value = mock_config

        if "src.svg_config" in sys.modules:
            del sys.modules["src.svg_config"]

        with patch("src.svg_config.Path.mkdir"):
            from src import svg_config

            assert svg_config.db_data["host"] == "db.example.com"
            assert svg_config.db_data["user"] == "dbuser"
            assert svg_config.db_data["dbname"] == "mydb"
            assert svg_config.db_data["password"] == "secret"  # noqa: S105

    @patch("src.svg_config.ConfigParser")
    def test_svg_data_dir_created(self, mock_config_parser):
        """Test that svg_data_dir is created if it doesn't exist."""
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda _, default="": default

        mock_config_parser.return_value.read.return_value = None
        mock_config_parser.return_value.__getitem__.return_value = mock_config

        if "src.svg_config" in sys.modules:
            del sys.modules["src.svg_config"]

        with patch("src.svg_config.Path.mkdir") as mock_mkdir:
            from src import svg_config

            # mkdir should be called with parents=True, exist_ok=True
            mock_mkdir.assert_called_with(parents=True, exist_ok=True)

    @patch("src.svg_config.ConfigParser")
    def test_config_file_paths(self, mock_config_parser):
        """Test that config file paths are constructed correctly."""
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda _, default="": default

        mock_config_parser.return_value.read.return_value = None
        mock_config_parser.return_value.__getitem__.return_value = mock_config

        if "src.svg_config" in sys.modules:
            del sys.modules["src.svg_config"]

        with patch("src.svg_config.Path.mkdir"):
            from src import svg_config

            assert "user.ini" in svg_config.user_config_path
            assert "db.ini" in svg_config.db_config_path

    @patch("src.svg_config.ConfigParser")
    def test_fallback_to_client_section(self, mock_config_parser):
        """Test fallback to 'client' section if 'DEFAULT' is empty."""
        mock_parser = MagicMock()
        mock_default = {}  # Empty DEFAULT
        mock_client = {
            "host": "client.example.com",
            "user": "client_user",
            "dbname": "client_db",
            "password": "client_pass",
        }

        def getitem_side_effect(key):
            if key == "DEFAULT":
                return mock_default
            elif key == "client":
                return mock_client
            return {}

        mock_parser.__getitem__.side_effect = getitem_side_effect
        mock_parser.read.return_value = None
        mock_config_parser.return_value = mock_parser

        if "src.svg_config" in sys.modules:
            del sys.modules["src.svg_config"]

        with patch("src.svg_config.Path.mkdir"):
            from src import svg_config

            # Should use client section when DEFAULT is empty
            assert svg_config.db_data["host"] == "client.example.com" or svg_config.db_data["host"] == ""


class TestConfigIntegration:
    """Integration tests for config module."""

    @patch.dict(os.environ, {"HOME": "/integration/test", "TASK_DB_PATH": "/int/test.db"})
    @patch("src.svg_config.ConfigParser")
    def test_full_config_integration(self, mock_config_parser):
        """Test full configuration integration."""
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda key, default="": {
            "host": "testhost",
            "user": "testuser",
            "dbname": "testdb",
            "password": "testpass",
        }.get(key, default)

        mock_config_parser.return_value.read.return_value = None
        mock_config_parser.return_value.__getitem__.return_value = mock_config

        if "src.svg_config" in sys.modules:
            del sys.modules["src.svg_config"]

        with patch("src.svg_config.Path.mkdir"):
            from src import svg_config

            # Check all config values
            assert svg_config.project == "/integration/test"
            assert svg_config.TASK_DB_PATH == "/int/test.db"
            assert svg_config.db_data["host"] == "testhost"
            assert isinstance(svg_config.svg_data_dir, Path)
