"""Compatibility package exposing the src.web modules."""

from pathlib import Path

_pkg_dir = Path(__file__).resolve().parent
_root_dir = _pkg_dir.parents[2]
_src_dir = _root_dir / "src" / "web"

__path__ = [str(_pkg_dir)]
if _src_dir.exists():
    __path__.append(str(_src_dir))
