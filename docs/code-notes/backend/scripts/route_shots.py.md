# Notes for `backend/scripts/route_shots.py`

Comments and docstrings moved out of [`backend/scripts/route_shots.py`](../../../../backend/scripts/route_shots.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../backend/scripts/route_shots.py#L1): Docstring

> A picture of every screen, at three widths, for comparing before and after.
>
> There is no visual regression suite and this is not one. It is the smallest
> thing that makes a change to 314 inline styles reviewable: shoot every route
> before touching anything, shoot them again after, and look at the pairs.
>
>     make shots out=/tmp/before
>     …change something…
>     make shots out=/tmp/after
>
> A console that breaks quietly breaks in one state on one width, which is
> exactly what nobody checks by hand.
>
> Not every difference is a change you made. These shoot live data, so a route
> whose rows carry timestamps, counts or a capture still in progress differs
> between two runs of this script with nothing edited in between -- Recordings and
> Skills both do. The way to tell: shoot twice without changing anything and diff
> those, then treat that set as noise.

## module, [line 18](../../../../backend/scripts/route_shots.py#L18): Note on the line above

Code: `WIDTHS = (1512, 900, 560)`

> Desktop, a narrow laptop, and the width where the bar and the tables stop
> fitting -- which is where this product's layout problems have all been.

## module, [line 12](../../../../backend/scripts/route_shots.py#L12): Comment

Code: `"/console",`

> Bar order, left to right, so a contact sheet reads the way the nav does.
> A route nobody shoots is a route nobody compares -- and a removed page
> left in here shoots its redirect target twice and calls it coverage.

## `main`, [line 37](../../../../backend/scripts/route_shots.py#L37): Comment

Code: `page.goto(f"{CONSOLE}/console", wait_until="domcontentloaded")`

> The credential is per origin, so it is planted once and every
> route after this one is already signed in.

## `main`, [line 42](../../../../backend/scripts/route_shots.py#L42): Comment

Code: `page.wait_for_timeout(1200)`

> A table that is still fetching is a skeleton, and a
> skeleton compared against a table is a diff on every row.
