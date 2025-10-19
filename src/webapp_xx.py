from __future__ import annotations

from collections import namedtuple
# import sys
# import os
import threading
import uuid

from flask import Flask, render_template, request, redirect, url_for, jsonify
from asgiref.wsgi import WsgiToAsgi

from web.web_run_task import run_task
# from uvicorn.main import logger
# import logging
# logger = logging.getLogger(__name__)

from svg_translate import logger, config_logger
from web.task_store_pymysql import TaskStorePyMysql, TaskAlreadyExistsError
from svg_config import SECRET_KEY

config_logger("ERROR")  # DEBUG # ERROR # CRITICAL

TASK_STORE_New = TaskStorePyMysql()


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


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates")
    app.config["SECRET_KEY"] = SECRET_KEY

    @app.get("/")
    def index():
        task_id = request.args.get("task_id")
        task = TASK_STORE_New.get_task(task_id) if task_id else None

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

        existing_task = TASK_STORE_New.get_active_task_by_title(title)
        if existing_task:
            return redirect(url_for("index", task_id=existing_task["id"], error="task-active"))

        task_id = uuid.uuid4().hex
        try:
            TASK_STORE_New.create_task(
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
        t = threading.Thread(target=run_task, args=(TASK_STORE_New, task_id, title, args), daemon=True)
        # ---
        t.start()

        return redirect(url_for("index", task_id=task_id))

    @app.get("/index2")
    def index2():
        task_id = request.args.get("task_id")
        task = TASK_STORE_New.get_task(task_id) if task_id else None

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
        task = TASK_STORE_New.get_task(task_id)
        if not task:
            logger.debug(f"Task {task_id} not found")
            return jsonify({"error": "not-found"}), 404
        return jsonify(task)

    return app


def create_asgi_app():
    # Expose ASGI wrapper for uvicorn
    return WsgiToAsgi(create_app())


if __name__ == "__main__":
    # Optional: run with uvicorn if available; otherwise, fallback to Flask dev server
    try:
        import uvicorn

        uvicorn.run("webapp:create_asgi_app", host="127.0.0.1", port=8200, factory=True)
    except Exception:
        app = create_app()
        app.run(host="127.0.0.1", port=8200, debug=True)
