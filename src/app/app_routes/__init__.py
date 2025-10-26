
from .auth.routes import bp_auth
from .main.routes import bp_main
from .cancel_restart.routes import bp_tasks_managers
from .tasks.routes import bp_tasks, close_task_store

__all__ = [
    "bp_auth",
    "bp_main",
    "bp_tasks",
    "bp_tasks_managers",
    "close_task_store",
]
