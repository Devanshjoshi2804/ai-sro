"""Parameter names, derived from where the value was found.

No model is involved: the captured payload already uses the vocabulary of the
system being automated, and invented names would not match it.
"""

from __future__ import annotations

import re

from sro.application.induction import jsonutil
from sro.application.induction.sites import (
    ActionValueSite,
    HeaderSite,
    JsonBodySite,
    Site,
    TextBodySite,
    UrlPathSite,
    UrlQuerySite,
    url_path_segments,
)

CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
"""Where ``shipmentId`` becomes two words. Shared, because a second copy of
this that disagreed about digits would split field names one way for naming
and another way for deciding what is a credential."""
_NON_IDENTIFIER = re.compile(r"[^0-9a-zA-Z]+")


def snake_case(text: str) -> str:
    """``shipmentId`` -> ``shipment_id``; ``Order Number`` -> ``order_number``."""
    spaced = CAMEL_BOUNDARY.sub("_", text)
    cleaned = _NON_IDENTIFIER.sub("_", spaced).strip("_").lower()
    if not cleaned or cleaned[0].isdigit():
        cleaned = f"value_{cleaned}" if cleaned else "value"
    return cleaned


def _singular(word: str) -> str:
    # Naive by choice: getting `entries` or `boxes` slightly wrong still yields a
    # readable name, which is not worth an inflection dependency.
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def suggest_name(site: Site, *, url: str = "", field_label: str | None = None) -> str:
    match site:
        case JsonBodySite(pointer):
            tokens = [token for token in jsonutil.parse(pointer) if not token.isdigit()]
            return snake_case(tokens[-1]) if tokens else "body_value"

        case UrlQuerySite(key):
            return snake_case(key)

        case UrlPathSite(index):
            # The segment before an id usually names it: /shipments/12345.
            # Segments come from the same helper the sites are indexed against;
            # splitting the whole URL here would count the scheme and host and
            # name every path parameter after the wrong segment.
            segments = url_path_segments(url)
            if index > 0 and index - 1 < len(segments):
                return f"{snake_case(_singular(segments[index - 1]))}_id"
            return f"path_{index}"

        case HeaderSite(name):
            # `X-Wave-Id` reads as `wave_id`: the `x-` prefix says the header is
            # non-standard, which is not information the parameter needs.
            cleaned = name[2:] if name.lower().startswith("x-") else name
            return snake_case(cleaned)

        case ActionValueSite():
            return snake_case(field_label) if field_label else "input_value"

        case TextBodySite():
            return "request_body"


def singular(word: str) -> str:
    """One of whatever this is, as far as spelling alone can say.

    Deliberately shallow -- no dictionary, no stemmer. `addresses` has to give
    back `address` and not `addresse`, which is what a bare trailing-s rule
    produced and what then appeared in every sentence the system said out loud:
    "list every addresse at SG". `-es` only collapses after the endings that
    take it, because `modes` is not `mod`.
    """
    lowered = word
    if len(lowered) > 3 and lowered.endswith("ies"):
        return f"{lowered[:-3]}y"
    if (
        len(lowered) > 4
        and lowered.endswith("es")
        and lowered[:-2].endswith(("s", "x", "z", "ch", "sh"))
    ):
        return lowered[:-2]
    if len(lowered) > 3 and lowered.endswith("s") and not lowered.endswith(("ss", "us", "is")):
        return lowered[:-1]
    return lowered


def deduplicate(preferred: str, taken: set[str]) -> str:
    """Suffix a colliding name rather than merging two distinct parameters."""
    if preferred not in taken:
        return preferred
    suffix = 2
    while f"{preferred}_{suffix}" in taken:
        suffix += 1
    return f"{preferred}_{suffix}"
