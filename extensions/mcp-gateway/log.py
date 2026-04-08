"""Logging configuration for the MCP Gateway.

Configures Python's logging module with Rich output when available.
All other modules import this as ``import log`` and call
``log.getLogger(name)`` — this returns a real ``logging.Logger``.
"""

from __future__ import annotations

import logging


def _configure() -> None:
    handlers: list[logging.Handler] = []
    try:
        from rich.console import Console
        from rich.logging import RichHandler

        handlers.append(
            RichHandler(console=Console(stderr=True), rich_tracebacks=True)
        )
    except ImportError:
        handlers.append(logging.StreamHandler())

    logging.basicConfig(level=logging.INFO, format="%(message)s", handlers=handlers)


_configure()


def getLogger(name: str = "") -> logging.Logger:
    return logging.getLogger(name)
