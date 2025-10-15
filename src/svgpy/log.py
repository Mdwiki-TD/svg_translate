
import logging

logger = logging.getLogger(__name__)


def config_logger():

    logging.basicConfig(
        level=logging.DEBUG if "DEBUG" in sys.argv else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
