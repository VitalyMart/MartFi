import logging
import sys

formatter = logging.Formatter(
    fmt="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)

logger = logging.getLogger("back")
logger.setLevel(logging.INFO)
logger.addHandler(handler)
logger.propagate = False 

__all__ = ["logger"]