
import json
import datetime
from typing import Any, Optional


def _serialize(value: Any) -> Optional[str]:
    """
    Serialize a Python value to a JSON string suitable for storage, or return None for missing values.

    Parameters:
        value (Any): The Python value to serialize; if `None`, no serialization is performed.

    Returns:
        Optional[str]: JSON string of `value` with Unicode preserved (`ensure_ascii=False`), or `None` if `value` is `None`.
    """
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _normalize_title(title: str) -> str:
    """
    Normalize a title for duplicate detection.

    Returns:
        normalized (str): The title with surrounding whitespace removed and casefold applied.
    """
    title = title.replace("_", " ")
    return title.strip().casefold()


def _deserialize(value: Optional[str]) -> Any:
    """
    Deserialize a JSON-formatted string into a Python object.

    Parameters:
        value (Optional[str]): A JSON-formatted string, or None.

    Returns:
        The Python object produced by parsing `value`, or `None` if `value` is `None`.
    """
    if value is None:
        return None
    return json.loads(value)


def _current_ts() -> str:
    # Store in UTC. MySQL DATETIME has no TZ; keep application-level UTC.
    """
    Return the current UTC timestamp formatted for MySQL DATETIME.

    Returns:
        A string of the current UTC time in the format "YYYY-MM-DD HH:MM:SS".
    """
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S")
