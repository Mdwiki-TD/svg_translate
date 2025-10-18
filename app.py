from __future__ import annotations

from collections import namedtuple
# import sys
import os
import threading
import uuid
from typing import Dict, Any

from flask import Flask, render_template, request, redirect, url_for, jsonify
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
        title = request.form.get("title", "").strip()
        if not title:
            return redirect(url_for("index"))

        task_id = uuid.uuid4().hex
        with TASKS_LOCK:
            TASKS[task_id] = {
                "status": "Pending",
                "data": None,
                "title": title,
                "form": {x : request.form.get(x) for x in request.form},
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

    return app


def create_asgi_app():
    # Expose ASGI wrapper for uvicorn
    return WsgiToAsgi(create_app())


if __name__ == "__main__":
    # Optional: run with uvicorn if available; otherwise, fallback to Flask dev server
    try:
        import uvicorn

        # uvicorn.run("webapp:create_asgi_app", host="127.0.0.1", port=8200, factory=True)
        uvicorn.run("webapp:create_asgi_app", factory=True)
    except Exception:
        app = create_app()
        # app.run(host="127.0.0.1", port=8200, debug=True)
        app.run()
