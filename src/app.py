from __future__ import annotations

from collections import namedtuple
from logging import debug
import sys
import threading
import uuid

from flask import Flask, render_template, request, redirect, url_for, jsonify
# from asgiref.wsgi import WsgiToAsgi

from web.web_run_task import run_task
# from uvicorn.main import logger
# import logging
# logger = logging.getLogger(__name__)

from svg_translate import logger, config_logger
from web.task_store import TaskAlreadyExistsError, TaskStore
from svg_config import TASK_DB_PATH, SECRET_KEY

config_logger("ERROR")  # DEBUG # ERROR # CRITICAL

TASK_STORE = TaskStore(TASK_DB_PATH)

app = Flask(__name__, template_folder="web/templates")
app.config["SECRET_KEY"] = SECRET_KEY


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


@app.get("/")
def index():
    task_id = request.args.get("task_id")
    task = TASK_STORE.get_task(task_id) if task_id else None

    if not task:
        task = {"error": "not-found"}
        logger.debug(f"Task {task_id} not found")

    error_code = request.args.get("error")
    error_message = None
    if error_code == "task-active":
        error_message = "A task for this title is already in progress."

    return render_template(
        "index.html",
        task_id=task_id,
        task=task,
        form=task.get("form", {}),
        error_message=error_message,
    )


@app.post("/")
def start():
    title = request.form.get("title", "").strip()
    if not title:
        return redirect(url_for("index"))

    # existing_task = TASK_STORE.get_active_task_by_title(title)
    # if existing_task: return redirect(url_for("index", task_id=existing_task["id"], error="task-active"))

    task_id = uuid.uuid4().hex
    try:
        TASK_STORE.create_task(
            task_id,
            title,
            form={x: request.form.get(x) for x in request.form}
        )
    except TaskAlreadyExistsError as exc:
        existing = exc.task
        return redirect(url_for("index", task_id=existing["id"], error="task-active"))
    except Exception as exc:
        logger.exception(f"Failed to create task: {exc}")
        return redirect(url_for("index", error="task-create-failed"))

    args = parse_args(request.form)
    # ---
    # t = threading.Thread(target=_run_task, args=(task_id, title, args), daemon=True)
    # ---
    t = threading.Thread(target=run_task, args=(TASK_STORE, task_id, title, args), daemon=True)
    # ---
    t.start()

    return redirect(url_for("index", task_id=task_id))


@app.get("/index2")
def index2():
    task_id = request.args.get("task_id")
    task = TASK_STORE.get_task(task_id) if task_id else None

    if not task:
        task = {"error": "not-found"}
        logger.debug(f"Task {task_id} not found")

    error_code = request.args.get("error")
    error_message = None
    if error_code == "task-active":
        error_message = "A task for this title is already in progress."

    return render_template(
        "index2.html",
        task_id=task_id,
        task=task,
        form=task.get("form", {}),
        error_message=error_message,
    )


@app.get("/status/<task_id>")
def status(task_id: str):
    task = TASK_STORE.get_task(task_id)
    if not task:
        logger.debug(f"Task {task_id} not found")
        return jsonify({"error": "not-found"}), 404
    return jsonify(task)


if __name__ == "__main__":
    debug = "debug" in sys.argv
    app.run(debug=debug)
