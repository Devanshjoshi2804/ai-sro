from __future__ import annotations

import re
from dataclasses import dataclass, replace

from sro.application.induction.naming import CAMEL_BOUNDARY
from sro.application.ports.vision import Screen
from sro.domain.recording.sensitivity import is_secret_field

_SECRET_ON_SCREEN = ("password", "passcode", "pin", "secret", "token", "otp", "mfa")


def _words_on(digest: str) -> set[str]:
    spaced = CAMEL_BOUNDARY.sub(" ", digest)
    return {word.lower() for word in re.findall(r"[A-Za-z]+", spaced)}


class EgressRefused(Exception): ...


@dataclass(frozen=True, slots=True)
class Redacted:
    screen: Screen
    removed: tuple[str, ...]


def prepare(screen: Screen, *, enabled: bool) -> Redacted:
    if not enabled:
        raise EgressRefused(
            "egress is switched off for this deployment; nothing is sent to a hosted model"
        )

    shown = _words_on(screen.text_digest)
    if compromising := [word for word in _SECRET_ON_SCREEN if word in shown]:
        raise EgressRefused(
            "the screen appears to be showing a credential field "
            f"({', '.join(compromising)}); it is not sent"
        )

    digest, removed = _strip(screen.text_digest)
    return Redacted(screen=replace(screen, text_digest=digest), removed=removed)


def _strip(digest: str) -> tuple[str, tuple[str, ...]]:
    kept: list[str] = []
    removed: list[str] = []
    for line in digest.splitlines():
        label = line.split(":", 1)[0].strip()
        if label and is_secret_field(label):
            removed.append(label)
        else:
            kept.append(line)
    return "\n".join(kept), tuple(removed)
