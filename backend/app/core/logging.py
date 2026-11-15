"""Logging setup: one consistent, readable format for the whole app."""

import logging

LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def configure_logging(level: str) -> None:
    logging.basicConfig(level=level, format=LOG_FORMAT, force=True)
    # Uvicorn's access log duplicates our request middleware.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
