from __future__ import annotations

import os
import threading
import uuid
from pathlib import Path
from typing import Dict, Any

from flask import Flask, render_template, request, redirect, url_for, jsonify
from asgiref.wsgi import WsgiToAsgi

from web.start_bot import one_title_web

# In-memory task storage for demo purposes
TASKS: Dict[str, Dict[str, Any]] = {}
TASKS_LOCK = threading.Lock()


def _compute_output_dir(title: str) -> Path:
    # Align with CLI behavior: store under repo svg_data/<slug>
    slug = title.split("/")[-1]
    base = Path(__file__).parent.parent / "svg_data"

    if not os.getenv("HOME"):
        base = Path("I:/SVG/svg_data")

    base.mkdir(parents=True, exist_ok=True)
    return base / slug


def _run_task(task_id: str, title: str):
    try:
        output_dir = _compute_output_dir(title)
        data = one_title_web(title, output_dir, titles_limit=1000, overwrite=False, do_upload=False)
        with TASKS_LOCK:
            TASKS[task_id]["data"] = data
            TASKS[task_id]["status"] = "completed" if not data.get("error") else "error"
    except Exception as e:
        with TASKS_LOCK:
            TASKS[task_id]["status"] = "error"
            TASKS[task_id]["data"] = {"error": str(e), "title": title, "stages": [{"name": "run", "status": "error", "message": str(e)}]}


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
        return render_template("index.html", task_id=task_id, task=task)

    @app.post("/")
    def start():
        title = request.form.get("title", "").strip()
        if not title:
            return redirect(url_for("index"))

        task_id = uuid.uuid4().hex
        with TASKS_LOCK:
            TASKS[task_id] = {"status": "pending", "data": None, "title": title}

        t = threading.Thread(target=_run_task, args=(task_id, title), daemon=True)
        t.start()

        return redirect(url_for("index", task_id=task_id))

    @app.get("/status/<task_id>")
    def status(task_id: str):
        with TASKS_LOCK:
            task = TASKS.get(task_id)
            if not task:
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
