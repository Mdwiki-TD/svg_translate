
from pathlib import Path
import pytest
from src.app.web import start_bot


@pytest.mark.parametrize(
    "extract_return, expected_message",
    [
        # No new translations found
        ({"existing": {"en": {}}, "new": {}}, "No translations found in main file"),
        # extract() returns an empty dict
        ({}, "No translations found in main file"),
        # extract() returns None
        (None, "Couldn't load translations from main file"),
    ],
)
def test_translations_task_stops_on_failure(
    monkeypatch, tmp_path, extract_return, expected_message
):
    stages = {"status": None, "message": None, "sub_name": None}

    dummy_main_path = tmp_path / "downloads"
    dummy_main_path.mkdir()

    fake_svg_path = dummy_main_path / "Example.svg"
    fake_svg_path.write_text("<svg></svg>")

    def fake_download_one_file(title, out_dir, index):
        return {"path": fake_svg_path}

    def fake_extract(path, case_insensitive):
        assert Path(path) == fake_svg_path
        return extract_return

    monkeypatch.setattr(start_bot, "download_one_file", fake_download_one_file)
    monkeypatch.setattr(start_bot, "extract", fake_extract)

    translations, updated_stages = start_bot.translations_task(
        stages, "Example.svg", dummy_main_path
    )

    assert translations == {}
    assert updated_stages["status"] == "Failed"
    assert updated_stages["message"] == expected_message
    
def test_translations_task_stops_when_no_new_translations(monkeypatch, tmp_path):
    stages = {"status": None, "message": None, "sub_name": None}

    dummy_main_path = tmp_path / "downloads"
    dummy_main_path.mkdir()

    fake_svg_path = dummy_main_path / "Example.svg"
    fake_svg_path.write_text("<svg></svg>")

    def fake_download_one_file(title, out_dir, index):
        return {"path": fake_svg_path}

    def fake_extract(path, case_insensitive):
        assert Path(path) == fake_svg_path
        return {"existing": {"en": {}}, "new": {}}

    monkeypatch.setattr(start_bot, "download_one_file", fake_download_one_file)
    monkeypatch.setattr(start_bot, "extract", fake_extract)

    translations, updated_stages = start_bot.translations_task(stages, "Example.svg", dummy_main_path)

    assert translations == {}
    assert updated_stages["status"] == "Failed"
    assert updated_stages["message"] == "No translations found in main file"
