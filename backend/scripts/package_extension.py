"""The zip the Chrome Web Store is given.

The extension has no build step, so the package is the tracked tree with some
things left out: the manifest `key` (the store issues its own for the item; an
unpacked build pins its id with one), the tests and their support files,
`src/page/` (only the backend image uses it), and everything outside
`manifest.json` and `src/`. Tracked only -- a stray `.DS_Store` or note in the
tree never ships.

Which deployment the package talks to is `deployment.generated.js`, written by
`make gen-deployment`: generate it first. The store gets an `https://` one;
`--allow-insecure` builds a zip for local QA and says so loudly.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXTENSION = ROOT / "new-chrome-extension"


DEPLOYMENT = "src/background/deployment.generated.js"


def _api_url(source: Path) -> str:
    text = (source / DEPLOYMENT).read_text() if (source / DEPLOYMENT).is_file() else ""
    found = re.search(r'DEFAULT_API_URL\s*=\s*"([^"]*)"', text)
    return found.group(1) if found else ""


def _tracked(source: Path) -> list[str]:
    listed = subprocess.run(
        ["git", "ls-files", "-z", "--", "src"],
        cwd=source,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return sorted(name for name in listed.split("\0") if name)


def package(source: Path, out: Path, *, allow_insecure: bool = False) -> Path:
    api = _api_url(source)
    if not api.startswith("https://"):
        if not allow_insecure:
            raise SystemExit(
                f"refusing to package: the deployment's API url is {api or 'not set'!r}, "
                "and the Web Store build must be https. Run "
                "`make gen-deployment api=https://...` first "
                "(or --allow-insecure for a local QA zip)."
            )
        print(f"WARNING: INSECURE BUILD, talks to {api!r} -- never upload this to the store", file=sys.stderr)
    manifest = json.loads((source / "manifest.json").read_text())
    manifest.pop("key", None)
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"ai-sro-{manifest['version']}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, indent=2) + "\n")
        for name in _tracked(source):
            parts = Path(name).parts
            if ".test." in parts[-1] or "test-support" in parts or parts[:2] == ("src", "page"):
                continue
            archive.write(source / name, name)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "dist")
    parser.add_argument("--allow-insecure", action="store_true", help="local QA zip: allow a non-https API url")
    args = parser.parse_args(argv)
    built = package(EXTENSION, args.out, allow_insecure=args.allow_insecure)
    print(f"wrote {built.relative_to(ROOT) if built.is_relative_to(ROOT) else built}")
    print(f"  {built.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
