"""Compatibility wrapper for legacy ``src.svg_config`` imports."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_MODULE_NAME = "src.app.svg_config"
_MODULE_PATH = Path(__file__).resolve().parent / "app" / "svg_config.py"
_spec = importlib.util.spec_from_file_location(_MODULE_NAME, _MODULE_PATH)
if _spec is None or _spec.loader is None:  # pragma: no cover - defensive
    raise ImportError(f"Cannot load module {_MODULE_NAME} from {_MODULE_PATH}")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

for _name in getattr(_module, "__all__", []):
    globals()[_name] = getattr(_module, _name)

__all__ = getattr(_module, "__all__", [])
