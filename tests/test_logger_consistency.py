"""Test that all modified modules use 'svg_translate' logger name."""
from __future__ import annotations

import pytest


@pytest.mark.parametrize("module_path,module_name", [
    ("src.app", "app"),
    ("src.app.app_routes.admin.admin_routes.coordinators", "coordinators"),
    ("src.app.app_routes.admin.admin_routes.templates", "templates"),
    ("src.app.app_routes.auth.oauth", "oauth"),
    ("src.app.app_routes.auth.routes", "routes"),
    ("src.app.app_routes.cancel_restart.routes", "cancel_restart_routes"),
    ("src.app.app_routes.explorer.compare", "compare"),
    ("src.app.app_routes.explorer.routes", "explorer_routes"),
    ("src.app.app_routes.explorer.thumbnail_utils", "thumbnail_utils"),
    ("src.app.app_routes.explorer.utils", "explorer_utils"),
    ("src.app.app_routes.main.routes", "main_routes"),
    ("src.app.app_routes.tasks.args_utils", "args_utils"),
    ("src.app.app_routes.tasks.routes", "task_routes"),
    ("src.app.app_routes.templates.routes", "templates_routes"),
    ("src.app.db.db_CoordinatorsDB", "db_CoordinatorsDB"),
    ("src.app.db.db_CreateUpdate", "db_CreateUpdate"),
    ("src.app.db.db_StageStore", "db_StageStore"),
    ("src.app.db.db_TasksListDB", "db_TasksListDB"),
    ("src.app.db.db_Templates", "db_Templates"),
    ("src.app.db.db_class", "db_class"),
    ("src.app.db.svg_db", "svg_db"),
    ("src.app.db.task_store_pymysql", "task_store_pymysql"),
    ("src.app.download_tasks.download", "download"),
    ("src.app.routes_utils", "routes_utils"),
    ("src.app.template_service", "template_service"),
    ("src.app.threads.fix_nested_tasks", "fix_nested_tasks"),
    ("src.app.threads.inject_tasks", "inject_tasks"),
    ("src.app.threads.task_threads", "task_threads"),
    ("src.app.threads.web_run_task", "web_run_task"),
    ("src.app.upload_tasks.up", "up"),
    ("src.app.upload_tasks.upload_bot", "upload_bot"),
    ("src.app.upload_tasks.upload_bot_new", "upload_bot_new"),
    ("src.app.users.admin_service", "admin_service"),
    ("src.app.users.store", "user_store"),
    ("src.app.web.commons.category", "category"),
    ("src.app.web.commons.text_bot", "text_bot"),
    ("src.app.web.start_bot", "start_bot"),
    ("src.app.web.wiki_site", "wiki_site"),
    ("src.log", "log"),
])
def test_module_logger_name(module_path, module_name):
    """Test that module uses 'svg_translate' as logger name."""
    import importlib
    
    module = importlib.import_module(module_path)
    
    # Check if module has a logger
    if hasattr(module, "logger"):
        assert module.logger.name == "svg_translate", \
            f"{module_path} logger should use 'svg_translate', got '{module.logger.name}'"
