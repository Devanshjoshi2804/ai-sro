from __future__ import annotations


class OverCap(Exception):
    code = "over_cap"


class RunRefused(Exception):
    code = "run_refused"
