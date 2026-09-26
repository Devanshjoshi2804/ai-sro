from __future__ import annotations

import hashlib
import os
import re
import socket
import subprocess
import sys
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

K_FIRST_PORT = 13000
K_LAST_PORT = 13999
K_HEALTHY_S = 300
K_PROBE_S = 2

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "infra" / "docker-compose.steel-worktree.yml"
ENV_FILE = ROOT / ".env.steel"
PROJECT = "steel-" + re.sub(r"[^a-z0-9_-]", "-", ROOT.name.lower())


def ports_for(root: Path, is_free: Callable[[int], bool]) -> tuple[int, int]:
    pairs = (K_LAST_PORT - K_FIRST_PORT + 1) // 2
    start = int.from_bytes(hashlib.sha256(str(root).encode()).digest()[:8]) % pairs
    for step in range(pairs):
        api = K_FIRST_PORT + 2 * ((start + step) % pairs)
        if is_free(api) and is_free(api + 1):
            return api, api + 1
    raise SystemExit(f"no free port pair in {K_FIRST_PORT}-{K_LAST_PORT}")


def _free(port: int) -> bool:
    with socket.socket() as probe:
        try:
            probe.bind(("0.0.0.0", port))  # noqa: S104
        except OSError:
            return False
    return True


def _running_ports() -> tuple[int, int] | None:
    found = []
    for inside in ("3000/tcp", "9223/tcp"):
        out = subprocess.run(  # noqa: S603
            ["docker", "port", f"{PROJECT}-steel-1", inside],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,
        )
        if out.returncode != 0 or not out.stdout.strip():
            return None
        found.append(int(out.stdout.split()[0].rsplit(":", 1)[1]))
    return found[0], found[1]


def _host_addresses() -> list[str]:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.connect(("192.0.2.1", 9))
        routed = str(probe.getsockname()[0])
    listed = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
    found = [routed, *(str(entry[4][0]) for entry in listed)]
    return [ip for ip in dict.fromkeys(found) if not ip.startswith("127.")]


def _seen_by_steel() -> str:
    server = ThreadingHTTPServer(("0.0.0.0", 0), BaseHTTPRequestHandler)  # noqa: S104
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        for ip in _host_addresses():
            reached = subprocess.run(  # noqa: S603
                [  # noqa: S607
                    "docker",
                    "exec",
                    f"{PROJECT}-steel-1",
                    "curl",
                    "-s",
                    "-o",
                    "/dev/null",
                    "-m",
                    str(K_PROBE_S),
                    f"http://{ip}:{server.server_address[1]}/",
                ],
                capture_output=True,
                check=False,
            )
            if reached.returncode == 0:
                return ip
    finally:
        server.shutdown()
        server.server_close()
    raise SystemExit("Steel reaches none of this host's addresses; set SRO_STEEL_SEES_HOST")


def _compose(*args: str, api: int = 0, cdp: int = 0) -> None:
    env = {**os.environ, "STEEL_API_PORT": str(api), "STEEL_CDP_PORT": str(cdp)}
    subprocess.run(  # noqa: S603
        ["docker", "compose", "-p", PROJECT, "-f", str(COMPOSE), *args],  # noqa: S607
        env=env,
        check=True,
    )


def up() -> None:
    api, cdp = _running_ports() or ports_for(ROOT, _free)
    _compose("up", "-d", "--wait", "--wait-timeout", str(K_HEALTHY_S), api=api, cdp=cdp)
    ENV_FILE.write_text(
        f"SRO_STEEL_BASE_URL=http://localhost:{api}\n"
        f"SRO_STEEL_CDP_URL=http://localhost:{cdp}\n"
        f"SRO_STEEL_SEES_HOST={_seen_by_steel()}\n"
    )
    print(f"{PROJECT}: api :{api}, cdp :{cdp}; wrote {ENV_FILE}")


def down() -> None:
    _compose("down")
    ENV_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    {"up": up, "down": down}[sys.argv[1]]()
