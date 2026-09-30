"""The zip the Chrome Web Store is given.

The extension has no build step, so the package is the tree with three things
left out: the manifest `key` (the store issues its own for the item; an
unpacked build pins its id with one), the tests and their support files, and
everything outside `manifest.json` and `src/`.

Which deployment the package talks to is `deployment.generated.js`, written by
`make gen-deployment`: generate it first.
"""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXTENSION = ROOT / "new-chrome-extension"


def package(source: Path, out: Path) -> Path:
    manifest = json.loads((source / "manifest.json").read_text())
    manifest.pop("key", None)
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"ai-sro-{manifest['version']}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, indent=2) + "\n")
        for path in sorted((source / "src").rglob("*")):
            if path.is_file() and ".test." not in path.name and "test-support" not in path.parts:
                archive.write(path, path.relative_to(source).as_posix())
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "dist")
    built = package(EXTENSION, parser.parse_args(argv).out)
    print(f"wrote {built.relative_to(ROOT) if built.is_relative_to(ROOT) else built}")
    print(f"  {built.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
