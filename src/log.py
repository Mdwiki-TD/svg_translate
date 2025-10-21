
import sys
import logging
logger = logging.getLogger(__name__)


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
    if not level:
        level = logging.DEBUG if "DEBUG" in sys.argv else logging.INFO

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
