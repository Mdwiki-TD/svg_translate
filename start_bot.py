"""

python3 I:/mdwiki/svg_repo/start_bot.py
python3 start_bot.py

tfj run svgbot --image python3.9 --command "$HOME/local/bin/python3 ~/bots/svg_translate/start_bot.py noup"

"""
"""Web entry-point for translating and uploading SVG assets."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional
import os
import sys
import uuid

from asgiref.wsgi import WsgiToAsgi
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from svg_translate import config_logger, start_on_template_title
from svg_translate.upload_files import start_upload

from user_info import password, username

config_logger("CRITICAL")


def _format_stage(name: str, status: str, message: str = "") -> Dict[str, str]:
    """Helper to normalize stage structure."""

    return {"name": name, "status": status, "message": message}


def _safe_directory_name(title: str) -> str:
    """Create a filesystem-friendly directory name for a template title."""

    sanitized = title.replace("Template:", "").replace("/", "_").strip()
    return sanitized or "unnamed"


def one_title(
    title: str,
    output_dir: Path,
    titles_limit: Optional[int] = None,
    overwrite: bool = False,
) -> Dict[str, object]:
    """Execute workflow for a single title and return structured progress data."""

    stages: List[Dict[str, str]] = []
    results: Dict[str, object] = {
        "title": title,
        "output_dir": str(output_dir),
        "files_to_upload": 0,
        "files_missing_path": 0,
        "nested_files": 0,
        "translations": 0,
        "uploaded": False,
    }

    stages.append(_format_stage("prepare-environment", "in-progress", "Preparing directories"))

    try:
        files_data = start_on_template_title(
            title,
            output_dir=output_dir,
            titles_limit=titles_limit,
            overwrite=overwrite,
        )
    except Exception as exc:  # pragma: no cover - defensive programming
        stages.append(
            _format_stage(
                "fetch-template",
                "failed",
                f"Unexpected error while processing template: {exc}",
            )
        )
        return {"stages": stages, "results": results, "error": str(exc)}

    if not files_data:
        stages.append(
            _format_stage(
                "fetch-template",
                "failed",
                "No data was returned for the requested title.",
            )
        )
        return {"stages": stages, "results": results, "error": "no-data"}

    stages[-1] = _format_stage(
        "prepare-environment",
        "completed",
        "Working directories ready.",
    )
    stages.append(
        _format_stage(
            "fetch-template",
            "completed",
            "Template metadata retrieved successfully.",
        )
    )

    translations = files_data.get("translations", {}).get("new", {})
    results["translations"] = len(translations)

    if translations:
        stages.append(
            _format_stage(
                "collect-translations",
                "completed",
                f"Identified {len(translations):,} translation entries.",
            )
        )
    else:
        stages.append(
            _format_stage(
                "collect-translations",
                "skipped",
                "No translations were found for the main template.",
            )
        )

    if not files_data.get("files"):
        stages.append(
            _format_stage(
                "collect-files",
                "skipped",
                "No additional files found to translate.",
            )
        )
        return {"stages": stages, "results": results, "error": "no-files"}

    stages.append(
        _format_stage(
            "collect-files",
            "completed",
            f"Collected {len(files_data['files']):,} file entries.",
        )
    )

    files_data["files"].pop(files_data.get("main_title"), None)

    main_title_link = f"[[:File:{files_data.get('main_title', title)}]]"
    files_to_upload = {
        name: meta for name, meta in files_data["files"].items() if meta.get("file_path")
    }
    results["files_to_upload"] = len(files_to_upload)

    no_file_path = len(files_data["files"]) - len(files_to_upload)
    results["files_missing_path"] = no_file_path
    results["nested_files"] = files_data.get("nested_files", 0)

    stages.append(
        _format_stage(
            "prepare-uploads",
            "completed",
            f"Prepared {len(files_to_upload):,} files for upload; {no_file_path:,} pending manual review.",
        )
    )

    upload_stage = _format_stage("upload", "skipped", "Uploads disabled by configuration.")

    if files_to_upload:
        if "noup" in sys.argv:
            upload_stage = _format_stage(
                "upload",
                "skipped",
                "Upload skipped via 'noup' flag.",
            )
        else:
            try:
                start_upload(files_to_upload, main_title_link, username, password)
            except Exception as exc:  # pragma: no cover - network side effect
                upload_stage = _format_stage(
                    "upload",
                    "failed",
                    f"Upload failed: {exc}",
                )
            else:
                upload_stage = _format_stage(
                    "upload",
                    "completed",
                    f"Uploaded {len(files_to_upload):,} file(s).",
                )
                results["uploaded"] = True

    stages.append(upload_stage)

    return {"stages": stages, "results": results, "error": None}


def create_app() -> Flask:
    """Create and configure the Flask application."""

    app = Flask(__name__)
    app.secret_key = os.getenv("SVG_TRANSLATE_SECRET_KEY", "dev-secret")

    base_output_dir = Path(os.getenv("SVG_TRANSLATE_OUTPUT_DIR", Path(__file__).parent / "svg_data"))
    base_output_dir.mkdir(parents=True, exist_ok=True)
    app.config["OUTPUT_BASE_DIR"] = base_output_dir
    app.config["TITLES_LIMIT"] = int(os.getenv("SVG_TRANSLATE_TITLES_LIMIT", "1000"))

    tasks: Dict[str, Dict[str, object]] = {}

    @app.route("/", methods=["GET", "POST"])
    def index():
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            if not title:
                return render_template(
                    "index.html",
                    error="Please provide a template title.",
                    task=None,
                )

            task_id = uuid.uuid4().hex
            output_dir = app.config["OUTPUT_BASE_DIR"] / _safe_directory_name(title)
            task_data = one_title(
                title,
                output_dir=output_dir,
                titles_limit=app.config["TITLES_LIMIT"],
            )
            task_data["id"] = task_id
            tasks[task_id] = task_data

            return redirect(url_for("index", task_id=task_id))

        task_id = request.args.get("task_id")
        task_data = tasks.get(task_id) if task_id else None
        return render_template("index.html", task=task_data, error=None)

    @app.route("/status/<task_id>")
    def task_status(task_id: str):
        task_data = tasks.get(task_id)
        if not task_data:
            return jsonify({"error": "Task not found"}), 404
        return jsonify(task_data)

    return app


def create_asgi_app():
    """Return an ASGI-compatible wrapper around the Flask app."""

    return WsgiToAsgi(create_app())


def main():
    """Run the web application using Uvicorn."""

    host = os.getenv("SVG_TRANSLATE_HOST", "0.0.0.0")
    port = int(os.getenv("SVG_TRANSLATE_PORT", "8000"))

    import uvicorn  # imported lazily to avoid hard dependency for library usage

    uvicorn.run("start_bot:create_asgi_app", host=host, port=port, factory=True)


if __name__ == "__main__":
    main()
