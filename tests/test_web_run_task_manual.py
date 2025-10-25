from types import SimpleNamespace

import pytest

from app.web import web_run_task as web_run_task_module


class DummyStore:
    def __init__(self):
        self.stage_updates = {}
        self.status_updates = []
        self.results = None
        self.data_updates = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def update_data(self, task_id, data):
        self.data_updates.append((task_id, data))

    def update_status(self, task_id, status):
        self.status_updates.append(status)

    def update_stage(self, task_id, stage_name, stage_state):
        self.stage_updates.setdefault(stage_name, []).append(stage_state.copy())

    def update_results(self, task_id, results):
        self.results = results

    def update_stage_column(self, task_id, stage_name, column_name, value):
        columns = getattr(self, "stage_column_updates", {})
        columns.setdefault(stage_name, []).append((column_name, value))
        self.stage_column_updates = columns


@pytest.mark.parametrize("manual_title", ["Manual.svg"])
def test_manual_main_title_overrides_pipeline(monkeypatch, tmp_path, manual_title):
    captured = {}

    dummy_store = DummyStore()

    def fake_task_store(db_data):
        return dummy_store

    monkeypatch.setattr(web_run_task_module, "TaskStorePyMysql", fake_task_store)
    monkeypatch.setattr(web_run_task_module, "_compute_output_dir", lambda title: tmp_path)

    def fake_text_task(stage, title):
        stage = stage.copy()
        stage["status"] = "Completed"
        return "wiki-text", stage

    def fake_titles_task(stage, text, titles_limit=None):
        stage = stage.copy()
        stage["status"] = "Failed"
        stage["message"] = "Found 1 titles, no main title found"
        return {"main_title": None, "titles": ["Example.svg"]}, stage

    def fake_translations_task(stage, main_title, output_dir_main):
        stage = stage.copy()
        stage["status"] = "Completed"
        captured["translations_main_title"] = main_title
        return ({"new": {"Example.svg": {"es": "Ejemplo"}}}, stage)

    def fake_download_task(task_id, stage, output_dir_main, titles, store):
        stage = stage.copy()
        stage["status"] = "Completed"
        captured["download_titles"] = list(titles)
        return ([str(output_dir_main / "Example.svg")], stage)

    def fake_inject_task(stage, files, translations, output_dir=None, overwrite=False):
        stage = stage.copy()
        stage["status"] = "Completed"
        return (
            {
                "saved_done": 1,
                "files": {
                    manual_title: {"file_path": str(output_dir / manual_title) if output_dir else manual_title},
                    "Example-translated.svg": {
                        "file_path": str(output_dir / "Example-translated.svg") if output_dir else "Example-translated.svg",
                        "new_languages": 1,
                    },
                },
            },
            stage,
        )

    def fake_upload_task(stage, files_to_upload, main_title, do_upload=None, user=None, store=None, task_id=""):
        stage = stage.copy()
        stage["status"] = "Completed"
        captured["upload_main_title"] = main_title
        captured["upload_files"] = dict(files_to_upload)
        return ({"done": len(files_to_upload)}, stage)

    monkeypatch.setattr(web_run_task_module, "text_task", fake_text_task)
    monkeypatch.setattr(web_run_task_module, "titles_task", fake_titles_task)
    monkeypatch.setattr(web_run_task_module, "translations_task", fake_translations_task)
    monkeypatch.setattr(web_run_task_module, "download_task", fake_download_task)
    monkeypatch.setattr(web_run_task_module, "inject_task", fake_inject_task)
    monkeypatch.setattr(web_run_task_module, "upload_task", fake_upload_task)

    captured_stats = {}

    def fake_save_files_stats(data, output_dir):
        captured_stats["data"] = data
        captured_stats["output_dir"] = output_dir

    monkeypatch.setattr(web_run_task_module, "save_files_stats", fake_save_files_stats)

    args = SimpleNamespace(
        titles_limit=10,
        overwrite=False,
        upload=False,
        ignore_existing_task=False,
        manual_main_title=manual_title,
    )

    web_run_task_module.run_task({}, "task123", "Template:Example", args, user_data={})

    titles_updates = dummy_store.stage_updates.get("titles", [])
    assert titles_updates, "Titles stage should be updated"
    final_titles_state = titles_updates[-1]
    assert final_titles_state.get("status") == "Completed"
    assert manual_title in final_titles_state.get("message", "")
    assert manual_title in final_titles_state.get("sub_name", "")

    assert captured["translations_main_title"] == manual_title
    assert captured["download_titles"] == ["Example.svg"]
    assert captured["upload_main_title"] == manual_title
    assert manual_title not in captured["upload_files"]  # filtered out before upload

    assert dummy_store.results is not None
    assert dummy_store.results["main_title"] == manual_title

    assert dummy_store.status_updates[-1] == "Completed"

    assert captured_stats["data"]["main_title"] == manual_title
