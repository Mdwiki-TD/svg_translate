import os
import logging
from pathlib import Path

home_dir = os.getenv("HOME") if os.getenv("HOME") else 'I:/SVG/svg_repo'

# Create log directory if needed
log_dir = Path(f"{home_dir}/logs")
log_dir.mkdir(parents=True, exist_ok=True)

# Define paths
all_log_path = log_dir / "app.log"
error_log_path = log_dir / "errors.log"

# Create main logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Handler for all logs
all_handler = logging.FileHandler(all_log_path)
all_handler.setLevel(logging.INFO)  # INFO, WARNING, etc.
all_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
all_handler.setFormatter(all_formatter)

# Handler for only ERROR and CRITICAL
error_handler = logging.FileHandler(error_log_path)
error_handler.setLevel(logging.ERROR)
error_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
error_handler.setFormatter(error_formatter)

# Attach handlers
logger.addHandler(all_handler)
logger.addHandler(error_handler)


def config_logger(level=None):
    """Configure the module-level logger with a standard formatter and level.

    Parameters:
        level (int | str | None): Logging level to apply. When None, the level is
            derived from command-line arguments (DEBUG when "DEBUG" is present,
            otherwise INFO). Accepts either numeric levels or their string names.

    Side Effects:
        Calls :func:`logging.basicConfig` to configure the root logger and updates
        this module's ``logger`` accordingly.
    """
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

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
