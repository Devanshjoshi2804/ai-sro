# Notes for `backend/scripts/steel_worktree.py`

Comments and docstrings for [`backend/scripts/steel_worktree.py`](../../../../backend/scripts/steel_worktree.py). Each note names the code it explains (function or class, then the line in the current file) and says what the code does and why.

## module, [line 1](../../../../backend/scripts/steel_worktree.py#L1): Docstring

> One local Steel per worktree: `make steel-up` / `make steel-down`.
>
> Every agent's tests used to share `ai-sro-steel-1` (:3010/:9223). Two or
> three agents running Steel tests at once ran it out of contexts: 502 on
> /json/version, "no browser attached", stalls and false failures. Each
> worktree now starts its own container from
> `infra/docker-compose.steel-worktree.yml` under the compose project
> `steel-<worktree basename>`, and writes the worktree's gitignored
> `.env.steel` (`SRO_STEEL_BASE_URL`, `SRO_STEEL_CDP_URL`,
> `SRO_STEEL_SEES_HOST`), which `backend/tests/conftest.py` loads. `down`
> removes only this project's container, never `ai-sro-steel-1` or another
> worktree's.

## `K_FIRST_PORT`, [line 14](../../../../backend/scripts/steel_worktree.py#L14): Constant

> Host ports for worktree Steels live in 13000-13999 (`K_LAST_PORT`), clear
> of the dev stack's 3010/3011/9223/9224 and of the ephemeral range, as
> 500 non-overlapping (API, CDP) pairs.

## `K_HEALTHY_S`, [line 16](../../../../backend/scripts/steel_worktree.py#L16): Constant

> Bound on `docker compose up --wait`: the container's own healthcheck
> (`x-steel` in docker-compose.yml, 20 retries of 10 s plus a first pull) is
> the signal; this only stops a Steel that never gets healthy from hanging
> `make steel-up` forever.

## `K_PROBE_S`, [line 17](../../../../backend/scripts/steel_worktree.py#L17): Constant

> How long one address gets to answer a curl from inside the container. An
> address the container cannot route to (a VPN's) hangs rather than refuses,
> so without a bound one bad candidate would stall `steel-up`.

## `ports_for`, [line 25](../../../../backend/scripts/steel_worktree.py#L25): Function

> The worktree's (API, CDP) host ports: a sha256 of its path picks a pair, so
> the same worktree gets the same pair every time; a pair with either port
> taken moves to the next pair, wrapping at the end of the range. Pairs start
> on even ports, so two worktrees' pairs never overlap.

## `_running_ports`, [line 44](../../../../backend/scripts/steel_worktree.py#L44): Function

> The ports this worktree's Steel already publishes, if it is running. A
> second `steel-up` reuses them -- re-deriving would find its own ports taken
> and move it -- so it only rewrites `.env.steel`.

## `_host_addresses`, [line 59](../../../../backend/scripts/steel_worktree.py#L59): Function

> Candidate host addresses: the one the default route picks first (on Linux
> that is the LAN address containers reach), then every address the host's
> own name resolves to (on macOS that lists each interface).

## `_seen_by_steel`, [line 68](../../../../backend/scripts/steel_worktree.py#L68): Function

> `SRO_STEEL_SEES_HOST`: the first host address Steel's container actually
> reaches, tested with a curl from inside it against a throwaway listener.
> The host cannot resolve `host.docker.internal`, and the default route's
> address is a full-tunnel VPN's on this machine (100.96.x), which the
> container cannot reach -- so reachability, not a routing guess, decides.
