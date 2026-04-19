"""Loguru setup with trace_id context."""
from __future__ import annotations

import sys

from loguru import logger

from aiops.core.config import settings

_configured = False


def setup_logging() -> None:
    global _configured
    if _configured:
        return
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.app.log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level:<7}</level> | "
            "<cyan>trace_id={extra[trace_id]}</cyan> | "
            "<cyan>{name}:{function}:{line}</cyan> - {message}"
        ),
    )
    logger.configure(extra={"trace_id": "-"})
    _configured = True


setup_logging()
log = logger
