"""Logging setup.

Without this, application logs are swallowed: uvicorn configures only its own
loggers, so anything the capture pipeline reports goes nowhere. Capture problems
are only diagnosable while they happen -- by review time the only evidence left
is whatever survived -- so this is not optional decoration.
"""

from __future__ import annotations

import logging

_FORMAT = "%(asctime)s %(levelname)-8s %(name)s %(message)s"


def configure_logging(*, level: str = "INFO") -> None:
    root = logging.getLogger()
    if root.handlers:
        # Something already owns logging (pytest, a worker harness). Adding a
        # second handler would duplicate every line.
        logging.getLogger("sro").setLevel(level)
        return

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(_FORMAT))
    root.addHandler(handler)
    root.setLevel(logging.WARNING)
    logging.getLogger("sro").setLevel(level)
