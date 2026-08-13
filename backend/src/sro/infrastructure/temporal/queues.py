"""Task queue names.

Their own module because both the worker and the client need them, and the
worker imports the container -- putting them there makes anything that schedules
work depend on the composition root.

Split by scarcity, not by feature: ``browser`` holds work tied to a browser
slot, so a slow induction can never starve session reaping.
"""

from __future__ import annotations

DEFAULT_QUEUE = "default"
BROWSER_QUEUE = "browser"
