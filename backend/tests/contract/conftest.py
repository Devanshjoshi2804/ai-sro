"""The ``postgres_url`` fixture, shared with the integration suite.

``test_openapi.py``'s fuzz test drives the real app, and the app's own
startup sweep (``on_start`` in ``sro.interface.http.app``) queries the
database named by ``SRO_DATABASE_URL`` -- which must be this throwaway,
migrated one, never the developer's own ``sro``.
"""

from __future__ import annotations

from tests.postgres import postgres_url  # noqa: F401  (fixture, used by name)
