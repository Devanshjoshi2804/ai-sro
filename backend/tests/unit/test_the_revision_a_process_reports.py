"""Every process says which commit it is running.

The failure this covers: an API left running for two days kept refusing runs
under a rule that had been fixed an hour earlier. Nothing was wrong with the
code, and nothing anywhere said which code was answering.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from sro import config
from sro.config import Settings, _git_head


def test_the_environment_wins_because_a_container_has_no_git(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SRO_REVISION", "deadbee")
    monkeypatch.setattr(
        config, "_git_head", lambda: pytest.fail("git was asked even though the build said so")
    )

    assert Settings(_env_file=None).revision == "deadbee"


def test_a_checkout_falls_back_to_git(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SRO_REVISION", raising=False)

    assert (
        Settings(_env_file=None).revision
        == subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],  # noqa: S607 - the same call under test
            cwd=Path(config.__file__).parent,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    )


@pytest.mark.parametrize(
    "why",
    [
        FileNotFoundError("no git here"),
        subprocess.CalledProcessError(128, "git"),
        subprocess.TimeoutExpired("git", 5),
    ],
)
def test_no_answer_is_unknown_rather_than_a_crash(
    monkeypatch: pytest.MonkeyPatch, why: Exception
) -> None:
    """A process that refused to start because it could not name itself would be
    a worse failure than the one this exists to catch."""

    def refuse(*_args: object, **_kwargs: object) -> None:
        raise why

    monkeypatch.setattr(subprocess, "run", refuse)

    assert _git_head() == "unknown"


def test_an_empty_answer_is_unknown_too(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        subprocess, "run", lambda *_a, **_k: subprocess.CompletedProcess([], 0, "  \n", "")
    )

    assert _git_head() == "unknown"
