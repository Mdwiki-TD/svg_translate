"""Compatibility package that re-exports the runtime code from the src layout."""

from importlib import import_module
from pathlib import Path
_pkg = import_module("src.svg_translate")

__all__ = list(getattr(_pkg, "__all__", []))
__doc__ = getattr(_pkg, "__doc__", None)

for name in __all__:
    globals()[name] = getattr(_pkg, name)

# Ensure both the installed package path and this compatibility wrapper are
# searched when importing submodules (e.g. ``svg_translate.commons``).
_current_dir = Path(__file__).resolve().parent
_pkg_path = list(getattr(_pkg, "__path__", []))
if str(_current_dir) not in _pkg_path:
    _pkg_path.append(str(_current_dir))
__path__ = _pkg_path

# Expose any public attributes that might not be listed in ``__all__`` but are
# commonly imported directly from the package (for example ``logger`` when
# ``__all__`` is missing).
for name, value in _pkg.__dict__.items():
    if name.startswith("_") or name in globals():
        continue
    globals()[name] = value
