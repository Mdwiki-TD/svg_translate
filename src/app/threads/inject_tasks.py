
import logging
from typing import Any
from CopySvgTranslate import start_injects  # type: ignore

logger = logging.getLogger(__name__)


def inject_task(
    stages: dict,
    files: list[str],
    translations,
    output_dir=None,
    overwrite=False
) -> tuple[dict, dict]:
    # ---
    """
    Perform translation injection on a list of files and write translated outputs under output_dir/translated.
    """
    if output_dir is None:
        stages["status"] = "Failed"
        stages["message"] = "inject task requires output_dir"
        return {}, stages
    # ---
    stages["message"] = f"inject 0/{len(files):,}"
    stages["status"] = "Running"
    # ---
    output_dir_translated = output_dir / "translated"
    output_dir_translated.mkdir(parents=True, exist_ok=True)
    # ---
    injects_result: dict[str, Any] = start_injects(files, translations, output_dir_translated, overwrite=overwrite)
    # ---
    success = injects_result.get('success') or injects_result.get('saved_done', 0)
    failed = injects_result.get('failed') or injects_result.get('no_save', 0)
    # ---
    stages["message"] = (
        f"Files: ({len(files):,}): "
        f"Success {success:,}, "
        f"Failed {failed:,}, "
        f"No changes {injects_result.get('no_changes', 0):,}, "
        f"Nested files: {injects_result.get('nested_files', 0):,}"
    )
    # ---
    stages["status"] = "Completed"
    # ---
    return injects_result, stages
