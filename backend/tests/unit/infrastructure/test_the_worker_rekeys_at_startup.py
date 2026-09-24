"""The migration a fix ships with, or does not.

`rekey_workflows` has said "run once at startup" since it was written, and
nothing ran it. The rule that makes a shape key changed on 2026-09-15 -- an
accessible name that is a paragraph is page copy, not an identifier -- and
every key minted before that change still carried the words of one mail.

Measured on the deployment, 2026-09-18: `Create a Customer Type` held nineteen
shape entries, most of them one mail's text, so a fresh demonstration of the
same job shared ONE entry with it and was mined as a second job with the same
name. The mail path then went silent for both -- a request naming a job this
tenant holds twice is one nothing can act on -- and the duplicate deleted by
hand at 21:20 was mined again by 01:13.
"""

from __future__ import annotations

import inspect

from sro.infrastructure.temporal import worker


def test_the_worker_recomputes_shape_keys_before_it_mines() -> None:
    source = inspect.getsource(worker.run)
    assert "rekey_everything" in source, (
        "nothing calls the rekey; a fix that ships without its migration is a fix for new rows only"
    )
    # Before the miner, because a pass run against stale keys is a pass that
    # proposes a duplicate of a job the rig already holds.
    assert source.index("rekey_everything") < source.index("mine_the_rig_lately"), source


def test_the_rekey_covers_every_tenant_that_has_ever_recorded_anything() -> None:
    source = inspect.getsource(worker.rekey_everything)
    assert "tenants_since" in source
    # From the epoch: a tenant that stopped recording last year still holds
    # workflows, and those are exactly the ones with the oldest keys.
    assert "1970" in source, source
