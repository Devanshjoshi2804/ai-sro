# Notes for `backend/tests/unit/interface/test_no_router_touches_the_unit_of_work.py`

Comments and docstrings moved out of [`backend/tests/unit/interface/test_no_router_touches_the_unit_of_work.py`](../../../../../../backend/tests/unit/interface/test_no_router_touches_the_unit_of_work.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../backend/tests/unit/interface/test_no_router_touches_the_unit_of_work.py#L1): Docstring

> A router that opens its own unit of work is a read the application layer never saw -- this is the audit finding that put the rule there. import-linter checks which modules a layer may import, not which methods it calls once imported, so it cannot see a router that legitimately imports `Container` for dependency injection and then reaches past the use cases it hands out. This is the only gate narrow enough to catch that.
