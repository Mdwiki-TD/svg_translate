
from .auth.routes import bp_auth
from .main.routes import bp_main
from .explorer.routes import bp_explorer
from .cancel_restart.routes import bp_tasks_managers
from .tasks.routes import bp_tasks, close_task_store
from .admin.routes import bp_admin

__all__ = [
    "bp_auth",
    "bp_main",
    "bp_explorer",
    "bp_tasks",
    "bp_tasks_managers",
    "bp_admin",
    "close_task_store",
]
