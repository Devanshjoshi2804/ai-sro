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

from sro.infrastructure.telemetry.whose import AsJson, Attribution, Louder, Plainly

_FORMAT = "%(asctime)s %(levelname)-8s %(name)s %(message)s"
_HANDLER = "sro"


def configure_logging(
    *, level: str = "INFO", as_json: bool = False, louder_for: frozenset[str] = frozenset()
) -> None:
    """`as_json` for a deployment whose logs are collected and queried; the
    plain shape is for a person reading a terminal, and is the default because
    a developer running this locally is the commoner case."""
    ours = logging.getLogger("sro")
    # The logger sits at the lowest level anything may be seen at, and the
    # filter holds the rest back: a filter can only narrow what a logger
    # already let through, so a tenant asked for at DEBUG has to be reachable
    # before anybody decides whether to keep it.
    floor = logging.getLevelNamesMapping().get(level.upper(), logging.INFO)
    ours.setLevel(logging.DEBUG if louder_for else floor)
    _shape = AsJson() if as_json else Plainly(_FORMAT)
    _loud = Louder(floor, frozenset(louder_for))

    # Before either branch, because which one this process takes says nothing
    # about whether uvicorn is serving it. uvicorn's own dictConfig puts
    # handlers on `uvicorn.access` and `uvicorn.error` and NOT on the root --
    # so the API, which is the one process with an access log to borrow, takes
    # the second branch below and reached this nowhere at all.
    _borrow_uvicorns(_shape)

    root = logging.getLogger()
    if root.handlers:
        # Something already owns logging (pytest, an OTel handler, a worker
        # harness). Deferring to it lost every line this system writes -- the
        # worker ran for an hour with an empty log and its session keeper could
        # not be told apart from one that had died. So our own records go to
        # our own handler, and do not propagate, which is also what stops them
        # being printed twice.
        if not any(handler.get_name() == _HANDLER for handler in ours.handlers):
            ours.addHandler(_stream(_shape, _loud))
            ours.propagate = False
        else:
            # Called twice -- a test, a worker that also builds an app -- and
            # the shape may have changed. The handler is reused; what it
            # renders with is not.
            for handler in ours.handlers:
                if handler.get_name() == _HANDLER:
                    handler.setFormatter(_shape)
        return

    root.addHandler(_stream(_shape, _loud))
    root.setLevel(logging.WARNING)


def _stream(shape: logging.Formatter, loud: Louder) -> logging.Handler:
    handler = logging.StreamHandler()
    handler.set_name(_HANDLER)
    handler.setFormatter(shape)
    handler.addFilter(loud)
    # On the handler rather than on a logger: a filter on a logger runs only
    # for records that logger made, and the point is that every record carries
    # this whichever of them wrote it.
    handler.addFilter(Attribution())
    return handler


_UVICORNS = ("uvicorn.access", "uvicorn.error")
"""The two loggers this process does not own.

Rendered the way everything else is, because they are otherwise the last
plain-text lines in a deployment whose logs are JSON, which is one parser away
from a collector dropping them.

`uvicorn.error` is where a websocket opening and a protocol giving up are
said, and it stays at whatever uvicorn set.
"""

_ACCESS = "uvicorn.access"
"""And this one is turned down, because this system writes that line itself.

uvicorn writes its access line from the protocol layer once the response is
done, OUTSIDE the task the handlers ran in -- so it carries a path and a
status and nobody at all, which on a deployment with twenty tenants makes the
one line written for every request the one line that cannot be attributed to
any of them. `interface.http.app.Attributing` writes the same fact from inside
the request, with whoever it turned out to be on it. Two lines per request
where one of them is the blind one is not a record, it is noise with a record
in it.

Turned down rather than silenced: uvicorn still says what it makes of a
request nothing in this system ever saw.
"""


def _borrow_uvicorns(shape: logging.Formatter) -> None:
    """Render uvicorn's own lines the way this deployment renders everything.

    Its handlers, not ours: uvicorn installs them before this runs and owns
    their lifetime, so this changes what they render with and leaves the
    plumbing alone. Nothing is added where uvicorn installed nothing -- a
    deployment that runs this app some other way is not one whose access log
    this should invent.

    The attribution is whatever the access line can honestly carry. Uvicorn
    writes it from the protocol layer once the response is done, outside the
    task the handlers ran in, so a tenant is not usually there -- what it does
    carry is the shape, the level and the time, in the same form as every
    other line.
    """
    for name in _UVICORNS:
        for handler in logging.getLogger(name).handlers:
            if not any(isinstance(one, Attribution) for one in handler.filters):
                handler.addFilter(Attribution())
            handler.setFormatter(shape)
    access = logging.getLogger(_ACCESS)
    if access.handlers:
        access.setLevel(logging.WARNING)
