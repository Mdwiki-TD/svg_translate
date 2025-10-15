
import sys
import logging

logger = logging.getLogger(__name__)


def config_logger(level=None):
    if not level:
        level = logging.DEBUG if "DEBUG" in sys.argv else logging.INFO

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
