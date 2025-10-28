import sys
import os
import logging
from pathlib import Path

# from app.config import settings
# Create log directory if needed
# log_dir_path = settings.paths.log_dir
log_dir_path = os.getenv("LOG_PATH", f"{os.path.expanduser('~')}/logs")

log_dir = Path(log_dir_path)
log_dir.mkdir(parents=True, exist_ok=True)

# Define paths
all_log_path = log_dir / "app.log"
error_log_path = log_dir / "errors.log"

# Create main logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Handler for all logs
all_handler = logging.FileHandler(all_log_path, encoding="utf-8")
all_handler.setLevel(logging.INFO)  # INFO, WARNING, etc.
all_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
all_handler.setFormatter(all_formatter)

# Handler for only ERROR and CRITICAL
error_handler = logging.FileHandler(error_log_path, encoding="utf-8")
error_handler.setLevel(logging.ERROR)
error_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
error_handler.setFormatter(error_formatter)


# Attach handlers
logger.addHandler(all_handler)
logger.addHandler(error_handler)


def config_console_logger(level=None):
    _nameToLevel = [
        'CRITICAL',
        'FATAL',
        'ERROR',
        'WARN',
        'WARNING',
        'INFO',
        'DEBUG',
        'NOTSET',
    ]
    level = level or logging.INFO

    # Console (stdout) handler
    console_handler = logging.StreamHandler(sys.stdout)
    # console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(console_handler)
    if level:
        console_handler.setLevel(level)
