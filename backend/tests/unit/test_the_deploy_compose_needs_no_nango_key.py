"""The deploy compose file renders on a box that has not set the Nango or signing keys.

Compose interpolates the whole file for any command, so a `${VAR:?}` on one service
blocks every other: the Nango secret key can only be read from Nango's own dashboard
once Nango is up, so requiring it up front means Nango can never be started.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

COMPOSE = Path(__file__).resolve().parents[3] / "infra" / "docker-compose.deploy.yml"


@pytest.mark.skipif(shutil.which("docker") is None, reason="no docker on this machine")
def test_compose_config_renders_without_the_nango_secret_key_or_the_signing_key(
    tmp_path: Path,
) -> None:
    required = set(re.findall(r"\$\{(\w+):\?", COMPOSE.read_text()))
    keys = {"SRO_NANGO_SECRET_KEY", "SRO_CONNECTOR_SIGNING_KEY"}
    env = tmp_path / "dummy.env"
    env.write_text("".join(f"{name}=x\n" for name in sorted(required - keys)))

    for target in ("config", "config nango-server"):
        done = subprocess.run(  # noqa: S603 - a fixed command on a repo file
            [
                shutil.which("docker") or "docker",
                "compose",
                "-f",
                str(COMPOSE),
                "--env-file",
                str(env),
                *target.split(),
            ],
            capture_output=True,
            text=True,
            env={k: v for k, v in os.environ.items() if k not in keys},
        )
        assert done.returncode == 0, done.stderr[-400:]
