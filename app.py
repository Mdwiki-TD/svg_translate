from __future__ import annotations

from collections import namedtuple
# import sys
import os
import threading
import uuid
from typing import Dict, Any

from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from asgiref.wsgi import WsgiToAsgi

from web.web_run_task import run_task
# from uvicorn.main import logger
# import logging
# logger = logging.getLogger(__name__)

from svg_translate import logger, config_logger

config_logger("ERROR")  # DEBUG # ERROR # CRITICAL

# In-memory task storage for demo purposes
TASKS: Dict[str, Dict[str, Any]] = {}
TASKS_LOCK = threading.Lock()


def _normalize_title(title: str) -> str:
    """Return a normalized form of a title for duplicate detection."""
    return title.strip().casefold()


def parse_args(request_form):
    Args = namedtuple("Args", ["titles_limit", "overwrite", "upload"])
    # ---
    upload = bool(request_form.get("upload"))
    # ---
    upload = False
    # ---
    result = Args(
        titles_limit=request_form.get("titles_limit", 1000, type=int),
        overwrite=bool(request_form.get("overwrite")),
        upload=upload
    )
    # ---
    return result


app = Flask(__name__, template_folder="web/templates")
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")


@app.get("/")
def index():
    task_id = request.args.get("task_id")
    task = None
    if task_id:
        with TASKS_LOCK:
            task = TASKS.get(task_id)

    if not task:
        task = {"error": "not-found"}
        logger.debug(f"Task {task_id} not found")

    return render_template("index.html", task_id=task_id, task=task, form=task.get("form", {}))


@app.post("/")
def start():
    raw_title = request.form.get("title", "")
    title = raw_title.strip()
    if not title:
        return redirect(url_for("index"))

    with TASKS_LOCK:
        normalized_title = _normalize_title(title)
        for existing_id, existing_task in TASKS.items():
            existing_normalized = existing_task.get("normalized_title")
            if existing_normalized is None and existing_task.get("title"):
                existing_normalized = _normalize_title(existing_task.get("title", ""))
            if (
                existing_normalized == normalized_title
                and existing_task.get("status") not in {"Completed", "Failed"}
            ):
                flash({"title": title, "task_id": existing_id}, "duplicate_task")
                return redirect(url_for("index", task_id=existing_id))

        task_id = uuid.uuid4().hex
        TASKS[task_id] = {
            "status": "Pending",
            "data": None,
            "title": title,
            "normalized_title": normalized_title,
            "form": {x: request.form.get(x) for x in request.form}
        }

    args = parse_args(request.form)
    # ---
    # t = threading.Thread(target=_run_task, args=(task_id, title, args), daemon=True)
    # ---
    t = threading.Thread(target=run_task, args=(task_id, title, args, TASKS, TASKS_LOCK), daemon=True)
    # ---
    t.start()

    return redirect(url_for("index", task_id=task_id))


@app.get("/index2")
def index2():
    task_id = request.args.get("task_id")
    task = None
    if task_id:
        with TASKS_LOCK:
            task = TASKS.get(task_id)

    if not task:
        task = {"error": "not-found"}
        logger.debug(f"Task {task_id} not found")

    return render_template("index2.html", task_id=task_id, task=task, form=task.get("form", {}))


@app.get("/status/<task_id>")
def status(task_id: str):
    with TASKS_LOCK:
        task = TASKS.get(task_id)
        if not task:
            logger.debug(f"Task {task_id} not found")
            return jsonify({"error": "not-found"}), 404
        return jsonify(task)


if __name__ == "__main__":
    app.run()
