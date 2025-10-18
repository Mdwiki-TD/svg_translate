import pytest
from urllib.parse import urlparse, parse_qs

pytest.importorskip("flask")

import webapp


def test_duplicate_task_submission_shows_warning(monkeypatch):
    """Posting the same title twice should warn instead of creating a new task."""

    def fake_run_task(task_id, title, args, tasks, lock):
        with lock:
            tasks[task_id]["status"] = "Running"

    monkeypatch.setattr(webapp, "run_task", fake_run_task)

    app = webapp.create_app()
    app.config.update(TESTING=True)

    with webapp.TASKS_LOCK:
        webapp.TASKS.clear()

    client = app.test_client()

    first_response = client.post(
        "/",
        data={"title": "Example Task", "titles_limit": "5"},
        follow_redirects=False,
    )
    assert first_response.status_code == 302
    first_location = first_response.headers["Location"]
    parsed_first = urlparse(first_location)
    first_task_id = parse_qs(parsed_first.query)["task_id"][0]

    with webapp.TASKS_LOCK:
        assert len(webapp.TASKS) == 1
        assert first_task_id in webapp.TASKS

    second_response = client.post(
        "/",
        data={"title": "  example task  ", "titles_limit": "5"},
        follow_redirects=False,
    )
    assert second_response.status_code == 302
    second_location = second_response.headers["Location"]
    parsed_second = urlparse(second_location)
    second_task_id = parse_qs(parsed_second.query)["task_id"][0]

    assert second_task_id == first_task_id

    follow_response = client.get(second_location)
    html = follow_response.get_data(as_text=True)

    assert "already running" in html
    assert "alert alert-warning" in html
    assert f"/?task_id={first_task_id}#progress-section" in html

    with webapp.TASKS_LOCK:
        assert len(webapp.TASKS) == 1
