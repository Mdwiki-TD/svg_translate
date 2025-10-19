"""Compatibility package that re-exports the runtime code from the src layout."""

from importlib import import_module
from pathlib import Path
import json
import shutil
from typing import Iterable, Mapping, MutableMapping, Optional

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

# ---------------------------------------------------------------------------
# Test shims
# ---------------------------------------------------------------------------
_core_extract = getattr(_pkg, "extract")

try:  # pragma: no cover - protective import, mirrors runtime layout
    from src.svg_translate.svgpy.bots.inject_bot import _inject as _core_inject
except Exception as exc:  # pragma: no cover - executed only if layout changes
    raise ImportError("The compatibility layer could not import the SVG inject implementation") from exc


def _simplify_translations(data: Mapping[str, object]) -> MutableMapping[str, MutableMapping[str, str]]:
    simplified: MutableMapping[str, MutableMapping[str, str]] = {}
    new_section = data.get("new") if isinstance(data, Mapping) else None
    if isinstance(new_section, Mapping):
        for key, value in new_section.items():
            if key == "default_tspans_by_id":
                continue
            if isinstance(value, Mapping):
                simplified[key] = {lang: str(text) for lang, text in value.items() if text is not None}
    if not simplified:
        old_section = data.get("old_way") if isinstance(data, Mapping) else None
        if isinstance(old_section, Mapping):
            for key, payload in old_section.items():
                translations = {}
                if isinstance(payload, Mapping):
                    lang_map = payload.get("_translations")
                    if isinstance(lang_map, Mapping):
                        for lang, texts in lang_map.items():
                            if isinstance(texts, Iterable) and not isinstance(texts, (str, bytes)):
                                texts = list(texts)
                                translations[lang] = str(texts[0]) if texts else ""
                            elif texts is not None:
                                translations[lang] = str(texts)
                if translations:
                    simplified[key] = translations
    return simplified


def extract(svg_file_path, output_path=None, *, case_insensitive=False):
    """Test-friendly wrapper around :func:`src.svg_translate.extract`."""

    result = _core_extract(svg_file_path, case_insensitive=case_insensitive)
    if result is None:
        return None

    simplified = _simplify_translations(result)

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(simplified, handle, ensure_ascii=False)

    return simplified


def inject(svg_file_path, mapping_paths, *, dry_run=False, overwrite=False, case_insensitive=False):
    """Inject translations and return detailed statistics."""

    svg_file_path = Path(svg_file_path)
    if not svg_file_path.exists():
        return None

    mapping_files = [Path(path) for path in mapping_paths]
    existing_mappings = [path for path in mapping_files if path.exists()]
    if not existing_mappings:
        return None

    save_result = not dry_run
    backup_path: Optional[Path] = None
    if save_result and svg_file_path.exists():
        backup_path = svg_file_path.with_suffix(svg_file_path.suffix + ".bak")
        shutil.copy2(svg_file_path, backup_path)

    _tree, stats = _core_inject(
        svg_file_path,
        mapping_files=existing_mappings,
        overwrite=overwrite,
        case_insensitive=case_insensitive,
        save_result=save_result,
        output_file=svg_file_path if save_result else None,
    )

    if not stats or stats.get("error"):
        if backup_path and backup_path.exists():
            backup_path.unlink()
        return None

    if dry_run and backup_path and backup_path.exists():
        backup_path.unlink()

    return stats


# Ensure the shims are exported just like the runtime implementations.
if "extract" not in __all__:
    __all__.append("extract")
if "inject" not in __all__:
    __all__.append("inject")
