import importlib
import os
import sys
from pathlib import Path

import pytest


def reload_svg_config(monkeypatch):
    sys.modules.pop("src.svg_config", None)
    return importlib.import_module("src.svg_config")


@pytest.fixture
def temp_env(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("SVG_TRANSLATE_PROJECT_ROOT", str(tmp_path / "project"))
    monkeypatch.setenv("SVG_TRANSLATE_WWW_ROOT", str(tmp_path / "www"))
    monkeypatch.setenv("SVG_DATA_DIR", str(tmp_path / "data"))
    return tmp_path


class TestSvgConfig:
    def test_home_dir_sets_paths(self, temp_env, monkeypatch):
        svg_config = reload_svg_config(monkeypatch)
        assert svg_config.project == str(temp_env / "project")
        assert svg_config.project_www == str(temp_env / "www")

    def test_task_db_path_from_env(self, temp_env, monkeypatch):
        monkeypatch.setenv("TASK_DB_PATH", str(temp_env / "tasks.db"))
        svg_config = reload_svg_config(monkeypatch)
        assert svg_config.TASK_DB_PATH == str(temp_env / "tasks.db")

    def test_secret_key_from_env(self, temp_env, monkeypatch):
        monkeypatch.setenv("FLASK_SECRET_KEY", "my-secret-key")
        svg_config = reload_svg_config(monkeypatch)
        assert svg_config.SECRET_KEY == "my-secret-key"

        svg_config = reload_svg_config(monkeypatch)
        assert svg_config.db_data["host"] == "db.example.com"
        assert svg_config.db_data["user"] == "dbuser"

    def test_svg_data_dir_created(self, temp_env, monkeypatch):
        data_dir = Path(os.environ["SVG_DATA_DIR"])
        assert not data_dir.exists()
        reload_svg_config(monkeypatch)
        assert data_dir.exists()

