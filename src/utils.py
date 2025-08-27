"""
Shared utilities: logging + retry helpers.
"""

import logging
import time
from logging.handlers import RotatingFileHandler
from typing import Callable, Iterable, Type


def setup_logging(level: str = "INFO", log_file: str = "app.log") -> None:
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Root logger (shared across all modules)
    logger = logging.getLogger()
    logger.setLevel(log_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Clear existing handlers (important when rerunning in REPL or Jupyter)
    if logger.hasHandlers():
        logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (rotating file — avoids infinite log size)
    file_handler = RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=3)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


def retry(
    exceptions: Iterable[Type[BaseException]],
    tries: int = 5,
    base_delay: float = 0.5,
    backoff: float = 2.0,
    max_delay: float = 8.0,
) -> Callable:
    """
    Exponential backoff retry decorator.

    :param exceptions: tuple/list of exception classes to catch
    :param tries: total attempts
    :param base_delay: initial delay seconds
    :param backoff: multiplier
    :param max_delay: cap delay
    """
    exceptions = tuple(exceptions)

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            attempt = 0
            delay = base_delay
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions:
                    attempt += 1
                    if attempt >= tries:
                        raise
                    time.sleep(min(delay, max_delay))
                    delay *= backoff

        return wrapper

    return decorator
