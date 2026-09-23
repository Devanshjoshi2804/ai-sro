from __future__ import annotations

import logging

from sro.whose import AsJson, Attribution, Louder, Plainly

_FORMAT = "%(asctime)s %(levelname)-8s %(name)s %(message)s"
_HANDLER = "sro"


def configure_logging(
    *, level: str = "INFO", as_json: bool = False, louder_for: frozenset[str] = frozenset()
) -> None:
    ours = logging.getLogger("sro")
    floor = logging.getLevelNamesMapping().get(level.upper(), logging.INFO)
    ours.setLevel(logging.DEBUG if louder_for else floor)
    _shape = AsJson() if as_json else Plainly(_FORMAT)
    _loud = Louder(floor, frozenset(louder_for))

    _borrow_uvicorns(_shape)

    root = logging.getLogger()
    if root.handlers:
        if not any(handler.get_name() == _HANDLER for handler in ours.handlers):
            ours.addHandler(_stream(_shape, _loud))
            ours.propagate = False
        else:
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
    handler.addFilter(Attribution())
    return handler


_UVICORNS = ("uvicorn.access", "uvicorn.error")

_ACCESS = "uvicorn.access"


def _borrow_uvicorns(shape: logging.Formatter) -> None:
    for name in _UVICORNS:
        for handler in logging.getLogger(name).handlers:
            if not any(isinstance(one, Attribution) for one in handler.filters):
                handler.addFilter(Attribution())
            handler.setFormatter(shape)
    access = logging.getLogger(_ACCESS)
    if access.handlers:
        access.setLevel(logging.WARNING)
