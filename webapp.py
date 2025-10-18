from __future__ import annotations

from collections import namedtuple
# import sys
import os
import threading
import uuid
from pathlib import Path
from typing import Dict, Any

from flask import Flask, render_template, request, redirect, url_for, jsonify
from asgiref.wsgi import WsgiToAsgi
from uvicorn.main import logger

from web.start_bot import (
    save_files_stats,
    text_task,
    titles_task,
    translations_task,
    download_task,
    inject_task,
    upload_task,
    make_results_summary
)

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


def prase_args(request):
    # ---
    args = namedtuple("Args", ["titles_limit", "overwrite", "upload"])
    # ---
    args.titles_limit = request.get("titles_limit", 1000, type=int)
    args.overwrite = request.get("overwrite", False, type=bool)
    args.upload = request.get("upload", False, type=bool)
    # ---
    return args


def _run_task(task_id: str, title: str, args: Dict) -> None:
    output_dir = _compute_output_dir(title)
    # ---
    TASKS[task_id]["data"] = {
        "title": title,
        "stages": {
            "initialize": {
                "number": 1,
                "sub_name": "",
                "status": "Running",
                "message": "Starting workflow"
            },
            "get_text": {
                "sub_name": "",
                "number": 2,
                "status": "pending",
                "message": "Getting text"
            },
            "titles_task": {
                "sub_name": "",
                "number": 3,
                "status": "pending",
                "message": "Getting titles"
            },
            "translations_task": {
                "sub_name": "",
                "number": 4,
                "status": "pending",
                "message": "Getting translations"
            },
            "download_stats": {
                "sub_name": "",
                "number": 5,
                "status": "pending",
                "message": "Downloading files"
            },
            "inject_task": {
                "sub_name": "",
                "number": 6,
                "status": "pending",
                "message": "Injecting translations"
            },
            "upload_task": {
                "sub_name": "",
                "number": 7,
                "status": "pending",
                "message": "Uploading files"
            },
        }
    }
    # ---
    stages_list = TASKS[task_id]["data"]["stages"]
    # ---
    text, stages_list["get_text"] = text_task(stages_list["get_text"], title)
    # ---
    if not text:
        return
    # ---
    main_title, titles, stages_list["titles_task"] = titles_task(stages_list["titles_task"], text, titles_limit=args.titles_limit)
    # ---
    if not titles:
        return
    # ---
    output_dir_main = output_dir / "files"
    output_dir_main.mkdir(parents=True, exist_ok=True)
    # ---
    translations, stages_list["translations_task"] = translations_task(stages_list["translations_task"], main_title, output_dir_main)
    # ---
    if not translations:
        return
    # ---
    files, stages_list["download_stats"] = download_task(stages_list["download_stats"], output_dir_main, titles)
    # ---
    if not files:
        return
    # ---
    injects_result, stages_list["inject_task"] = inject_task(stages_list["inject_task"], files, translations, output_dir=output_dir, overwrite=args.overwrite)
    # ---
    if injects_result.get('saved_done', 0) == 0:
        logger.error("inject result saved 0 files")
        return
    # ---
    inject_files = {x: v for x, v in injects_result.get("files", {}).items() if x != main_title}
    # ---
    files_to_upload = {x: v for x, v in inject_files.items() if v.get("file_path")}
    # ---
    no_file_path = len(inject_files) - len(files_to_upload)
    # ---
    data = {
        "main_title": main_title,
        "translations": translations or {},
        "titles": titles,
        "files": files,
        "injects_result": injects_result,
    }
    # ---
    save_files_stats(data, output_dir)
    # ---
    upload_result, stages_list["upload_task"] = upload_task(stages_list["upload_task"], files_to_upload, main_title, args.upload)
    # ---
    with TASKS_LOCK:
        # ---
        TASKS[task_id]["results"] = make_results_summary(files, files_to_upload, no_file_path, injects_result, translations, main_title, upload_result)
        # ---
        TASKS[task_id]["status"] = "Completed" if not data.get("error") else "error"


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
        return render_template("index.html", task_id=task_id, task=task, title=task.get("title", ""))

    @app.post("/")
    def start():
        title = request.form.get("title", "").strip()
        if not title:
            return redirect(url_for("index"))

        task_id = uuid.uuid4().hex
        with TASKS_LOCK:
            TASKS[task_id] = {"status": "pending", "data": None, "title": title}

        args = prase_args(request.form)
        # ---
        t = threading.Thread(target=_run_task, args=(task_id, title, args), daemon=True)
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
        return render_template("index2.html", task_id=task_id, task=task, title=task.get("title", ""))

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
