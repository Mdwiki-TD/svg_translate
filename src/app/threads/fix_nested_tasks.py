
import logging
from pathlib import Path
from CopySvgTranslate import match_nested_tags, fix_nested_file

logger = logging.getLogger(__name__)


def fix_nested_task(
    stages: dict,
    files: list[str]
) -> tuple[dict, dict]:
    # ---
    stages["message"] = f"Analyze 0/{len(files):,}"
    stages["status"] = "Running"
    # ---
    data = {
        "all_files": len(files),
        "status": {
            "len_nested_files": 0,
            "fixed": 0,
            "not_fixed": 0,
        },
        "len_nested_tags_before": {0: 0},
        "len_nested_tags_after": {0: 0},
    }
    # ---
    nested_files = 0
    fixed = 0
    not_fixed = 0
    # ---
    for file in files:
        file_path = Path(str(file))
        # ---
        nested_tags = match_nested_tags(file)
        # ---
        len_nested = len(nested_tags)
        # ---
        data["len_nested_tags_before"].setdefault(len_nested, 0)
        data["len_nested_tags_before"][len_nested] += 1
        # ---
        if not nested_tags:
            continue
        # ---
        nested_files += 1
        # ---
        if len_nested > 10 :
            # ---
            data["len_nested_tags_after"].setdefault(len_nested, 0)
            data["len_nested_tags_after"][len_nested] += 1
            # ---
            not_fixed += 1
            continue
        # ---
        file_fixed = fix_nested_file(file_path, file_path)
        # ---
        if file_fixed:
            nested_tags = match_nested_tags(file_path)
            len_nested = len(nested_tags)
            # ---
            if not nested_tags:
                fixed += 1
                # ---
                data["len_nested_tags_after"][0] += 1
                # ---
                continue
        # ---
        data["len_nested_tags_after"].setdefault(len_nested, 0)
        data["len_nested_tags_after"][len_nested] += 1
        # ---
        not_fixed += 1
    # ---
    logger.debug(f"analyze_nested_tags files: {len(files):,} nested: {nested_files:,} fixed {fixed:,}, not_fixed {not_fixed:,}")
    # ---
    data["status"]["len_nested_files"] = nested_files
    data["status"]["fixed"] = fixed
    data["status"]["not_fixed"] = not_fixed
    # ---
    stages["message"] = (
        f"Files: ({len(files):,}): "
        f"Nested: {nested_files:,}, "
        f"Fixed: {fixed:,}, "
        f"Not fixed: {not_fixed:,}."
    )
    # ---
    stages["status"] = "Completed"
    # ---
    return data, stages
