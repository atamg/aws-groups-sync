"""
Shared utilities: logging + retry helpers.
"""

import logging
import time
from typing import Callable, Iterable, Type


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


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
