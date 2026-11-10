"""Centralized logging: console + rotating file handler, one logger per module."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)
_FORMATTER = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger, wiring handlers only once per name."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    file_handler = RotatingFileHandler(
        _LOG_DIR / "framework.log", maxBytes=5 * 1024 * 1024, backupCount=3
    )
    file_handler.setFormatter(_FORMATTER)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(_FORMATTER)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger
