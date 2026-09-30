"""The Chrome Web Store zip: what ships, and what does not.

The unpacked extension pins its id with a manifest `key`; the store issues its
own key for the item, so the package it is given carries none. Tests, test
support and fixtures are development files and stay out of what users install.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from scripts.package_extension import EXTENSION, package


def _tree(root: Path) -> Path:
    (root / "src" / "panel").mkdir(parents=True)
    (root / "src" / "panel" / "test-support").mkdir()
    (root / "fixtures").mkdir()
    (root / "manifest.json").write_text(json.dumps({"name": "X", "version": "1.2.3", "key": "K"}))
    (root / "src" / "panel" / "panel.js").write_text("export {}")
    (root / "src" / "panel" / "panel.test.mjs").write_text("test")
    (root / "src" / "panel" / "test-support" / "fake.js").write_text("fake")
    (root / "fixtures" / "batch.json").write_text("{}")
    (root / "README.md").write_text("dev")
    return root


def test_the_store_zip_ships_the_extension_without_its_key_or_its_tests(tmp_path: Path) -> None:
    built = package(_tree(tmp_path / "ext"), tmp_path / "out")
    assert built.name == "ai-sro-1.2.3.zip"
    with zipfile.ZipFile(built) as archive:
        names = set(archive.namelist())
        manifest = json.loads(archive.read("manifest.json"))
    assert names == {"manifest.json", "src/panel/panel.js"}
    assert "key" not in manifest and manifest["version"] == "1.2.3"


def test_the_real_extension_packages_with_what_it_needs_to_run(tmp_path: Path) -> None:
    built = package(EXTENSION, tmp_path)
    with zipfile.ZipFile(built) as archive:
        names = set(archive.namelist())
        manifest = json.loads(archive.read("manifest.json"))
    assert "key" not in manifest
    assert manifest["background"]["service_worker"] in names
    assert manifest["side_panel"]["default_path"] in names
    assert manifest["options_page"] in names
    assert not [n for n in names if ".test." in n or "test-support" in n or "fixtures" in n]
