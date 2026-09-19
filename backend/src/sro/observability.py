"""Logging setup.

Without this, application logs are swallowed: uvicorn configures only its own
loggers, so anything the capture pipeline reports goes nowhere. Capture problems
are only diagnosable while they happen -- by review time the only evidence left
is whatever survived -- so this is not optional decoration.

Every line also says whose work it was about. See
`sro.infrastructure.telemetry.whose`: the ids ride on the task rather than
through fifty-three modules of call sites, and this is where they are rendered.
"""

from __future__ import annotations

import logging

from sro.infrastructure.telemetry.whose import AsJson, Attribution, Plainly

_FORMAT = "%(asctime)s %(levelname)-8s %(name)s %(message)s"
_HANDLER = "sro"


def configure_logging(*, level: str = "INFO", as_json: bool = False) -> None:
    """`as_json` for a deployment whose logs are collected and queried; the
    plain shape is for a person reading a terminal, and is the default because
    a developer running this locally is the commoner case."""
    ours = logging.getLogger("sro")
    ours.setLevel(level)
    _shape = AsJson() if as_json else Plainly(_FORMAT)

    root = logging.getLogger()
    if root.handlers:
        # Something already owns logging (pytest, an OTel handler, a worker
        # harness). Deferring to it lost every line this system writes -- the
        # worker ran for an hour with an empty log and its session keeper could
        # not be told apart from one that had died. So our own records go to
        # our own handler, and do not propagate, which is also what stops them
        # being printed twice.
        if not any(handler.get_name() == _HANDLER for handler in ours.handlers):
            ours.addHandler(_stream(_shape))
            ours.propagate = False
        else:
            # Called twice -- a test, a worker that also builds an app -- and
            # the shape may have changed. The handler is reused; what it
            # renders with is not.
            for handler in ours.handlers:
                if handler.get_name() == _HANDLER:
                    handler.setFormatter(_shape)
        return

    root.addHandler(_stream(_shape))
    root.setLevel(logging.WARNING)


def _stream(shape: logging.Formatter) -> logging.Handler:
    handler = logging.StreamHandler()
    handler.set_name(_HANDLER)
    handler.setFormatter(shape)
    # On the handler rather than on a logger: a filter on a logger runs only
    # for records that logger made, and the point is that every record carries
    # this whichever of them wrote it.
    handler.addFilter(Attribution())
    return handler
