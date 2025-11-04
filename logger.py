# WikECD/logger.py
import logging
from typing import Optional

DEFAULT_FMT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def get_logger(name: str, level: int = logging.INFO, fmt: Optional[str] = None) -> logging.Logger:
    fmt = fmt or DEFAULT_FMT
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(fmt))
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger
