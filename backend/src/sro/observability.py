"""Logging setup.

Without this, application logs are swallowed: uvicorn configures only its own
loggers, so anything the capture pipeline reports goes nowhere. Capture problems
are only diagnosable while they happen -- by review time the only evidence left
is whatever survived -- so this is not optional decoration.
"""

from __future__ import annotations

import logging

_FORMAT = "%(asctime)s %(levelname)-8s %(name)s %(message)s"
_HANDLER = "sro"


def configure_logging(*, level: str = "INFO") -> None:
    ours = logging.getLogger("sro")
    ours.setLevel(level)

    root = logging.getLogger()
    if root.handlers:
        # Something already owns logging (pytest, an OTel handler, a worker
        # harness). Deferring to it lost every line this system writes -- the
        # worker ran for an hour with an empty log and its session keeper could
        # not be told apart from one that had died. So our own records go to
        # our own handler, and do not propagate, which is also what stops them
        # being printed twice.
        if not any(handler.get_name() == _HANDLER for handler in ours.handlers):
            ours.addHandler(_stream())
            ours.propagate = False
        return

    root.addHandler(_stream())
    root.setLevel(logging.WARNING)


def _stream() -> logging.Handler:
    handler = logging.StreamHandler()
    handler.set_name(_HANDLER)
    handler.setFormatter(logging.Formatter(_FORMAT))
    return handler
