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
    """
    Parse form data into an Args namedtuple containing task-related options.

    Parameters:
        request_form: A mapping-like object (e.g., Flask `request.form`) with submitted form values.

    Returns:
        Args: a namedtuple with fields:
            - titles_limit (int): value from "titles_limit" converted to int, defaulting to 1000 if absent.
            - overwrite (bool): boolean interpretation of the "overwrite" form field.
            - upload (bool): always `False` (the "upload" form field is ignored).
    """
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
    """
    Create and configure the Flask application with routes for the web UI and task management.

    The app exposes:
    - GET "/"       -> renders "index.html" with optional task lookup and human-friendly error messages.
    - POST "/"      -> validates form input, creates a new task (or redirects if an active task exists), starts a daemon thread to run the task, and redirects to the index for the created task.
    - GET "/index2" -> renders "index2.html" with the same task lookup and error semantics as the root index.
    - GET "/status/<task_id>" -> returns task data as JSON or a 404 JSON error if the task is not found.

    Returns:
        Flask: A configured Flask application instance ready to be served.
    """
    app = Flask(__name__, template_folder="templates")
    app.config["SECRET_KEY"] = SECRET_KEY

    @app.get("/")
    def index():
        """
        Render the main index page with task information and an optional error message.

        Reads `task_id` and `error` from the request query string, looks up the task from TASK_STORE_New, and if no task is found substitutes a `{"error": "not-found"}` task and logs a debug message. If `error` equals `"task-active"`, sets a human-readable error message. Renders "index.html" with context: `task_id`, `task`, `form` (from `task["form"]` if present), and `error_message`.

        Returns:
            The rendered HTML response for the index page containing the task context.
        """
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
        """
        Handle POSTed form data to start a new task with the provided title.

        Creates a new task record in TASK_STORE_New and starts a daemon thread to run the task. If a task with the same title is already active, redirects to the index with the existing task's id and error "task-active". If task creation fails, redirects to the index with error "task-create-failed". If the submitted title is empty, redirects to the index without creating a task.

        Returns:
            A Flask redirect response to the index page. On success the redirect includes `task_id` for the newly created task; on duplicate active task the redirect includes the existing task's `task_id` and `error="task-active"`; on creation failure the redirect includes `error="task-create-failed"`.
        """
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
        """
        Render the index2 page populated with task data and an optional error message.

        Reads an optional "task_id" and "error" from the request query string, includes the corresponding task (or {"error": "not-found"} if missing), the task's form data (if present), and an error message when "error" is "task-active".

        Returns:
            A rendered HTML response for "index2.html" with context keys `task_id`, `task`, `form`, and `error_message`.
        """
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
        """
        Provide task details as JSON for the given task id.

        Returns:
            If the task exists, a JSON response containing the task data.
            If the task does not exist, a JSON response `{"error": "not-found"}` with HTTP status 404.
        """
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
