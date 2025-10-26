"""Unit tests for args parsing utilities."""
from werkzeug.datastructures import MultiDict

from src.app.app_routes.tasks import args_utils


def test_parse_args_upload_disabled_by_config(monkeypatch):
    monkeypatch.setattr(args_utils, "DISABLE_UPLOADS", "1")
    form = MultiDict([("upload", "1")])
    parsed = args_utils.parse_args(form)
    assert parsed.upload is False


def test_parse_args_manual_main_title_and_limits(monkeypatch):
    monkeypatch.setattr(args_utils, "DISABLE_UPLOADS", "0")
    form = MultiDict(
        [
            ("manual_main_title", "  File:Example name.svg "),
            ("titles_limit", "50"),
            ("overwrite", "z"),
            ("upload", "1"),
        ]
    )
    parsed = args_utils.parse_args(form)
    assert parsed.manual_main_title == "Example name.svg"
    assert parsed.titles_limit == 50
    assert parsed.overwrite is True
    assert parsed.upload is True


def test_parse_args_empty_manual_main_title(monkeypatch):
    monkeypatch.setattr(args_utils, "DISABLE_UPLOADS", "0")
    form = MultiDict([])
    parsed = args_utils.parse_args(form)
    assert parsed.manual_main_title is None