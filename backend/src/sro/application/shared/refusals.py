from __future__ import annotations


class OverCap(Exception):
    code = "over_cap"


class Unattributed(Exception):
    """A model call was made for no tenant, so no cap or bill sees it."""


class RunRefused(Exception):
    code = "run_refused"
