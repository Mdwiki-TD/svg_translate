"""Unit tests for db_StageStore module."""
from __future__ import annotations


def test_logger_uses_svg_translate_name():
    """Test that the logger uses 'svg_translate' instead of __name__."""
    from src.app.db import db_StageStore
    assert db_StageStore.logger.name == "svg_translate"


def test_no_unused_imports():
    """Test that unused import 're' has been removed."""
    import ast
    from pathlib import Path
    
    # Read the source file
    source_file = Path("src/app/db/db_StageStore.py")
    source_code = source_file.read_text()
    
    # Parse the AST
    tree = ast.parse(source_code)
    
    # Check imports
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.extend([f"{node.module}.{alias.name}" for alias in node.names])
    
    # Verify 're' is not imported (the 'from re import I' was removed)
    assert not any("re" == imp or imp.startswith("re.") for imp in imports)