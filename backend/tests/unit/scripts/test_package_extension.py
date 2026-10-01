"""The Chrome Web Store zip: what ships, and what does not.

The unpacked extension pins its id with a manifest `key`; the store issues its
own key for the item, so the package it is given carries none. Tests, test
support and fixtures are development files and stay out of what users install.
"""

from __future__ import annotations

import json
import subprocess
import zipfile
from pathlib import Path

import pytest
from scripts.package_extension import EXTENSION, package


def _deployment(root: Path, api: str) -> None:
    (root / "src" / "background").mkdir(parents=True, exist_ok=True)
    (root / "src" / "background" / "deployment.generated.js").write_text(
        f'export const DEFAULT_API_URL = "{api}";\n'
    )


def _tree(root: Path, api: str = "https://sro.example/api") -> Path:
    (root / "src" / "panel").mkdir(parents=True)
    (root / "src" / "page").mkdir()
    (root / "src" / "page" / "page-code.js").write_text("backend image only")
    _deployment(root, api)
    (root / "src" / "panel" / "test-support").mkdir()
    (root / "fixtures").mkdir()
    (root / "manifest.json").write_text(json.dumps({"name": "X", "version": "1.2.3", "key": "K"}))
    (root / "src" / "panel" / "panel.js").write_text("export {}")
    (root / "src" / "panel" / "panel.test.mjs").write_text("test")
    (root / "src" / "panel" / "test-support" / "fake.js").write_text("fake")
    (root / "fixtures" / "batch.json").write_text("{}")
    (root / "README.md").write_text("dev")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    return root


def test_the_store_zip_ships_the_extension_without_its_key_or_its_tests(tmp_path: Path) -> None:
    built = package(_tree(tmp_path / "ext"), tmp_path / "out")
    assert built.name == "ai-sro-1.2.3.zip"
    with zipfile.ZipFile(built) as archive:
        names = set(archive.namelist())
        manifest = json.loads(archive.read("manifest.json"))
    assert names == {
        "manifest.json",
        "src/panel/panel.js",
        "src/background/deployment.generated.js",
    }
    assert "key" not in manifest and manifest["version"] == "1.2.3"


def test_a_stray_untracked_file_never_ships(tmp_path: Path) -> None:
    tree = _tree(tmp_path / "ext")
    (tree / "src" / "panel" / ".DS_Store").write_text("junk")
    (tree / "src" / "panel" / "notes.md").write_text("my notes")
    with zipfile.ZipFile(package(tree, tmp_path / "out")) as archive:
        assert not [n for n in archive.namelist() if "DS_Store" in n or "notes" in n]


@pytest.mark.parametrize("api", ["http://10.11.9.25:8088/api", ""])
def test_a_store_build_must_talk_to_https(tmp_path: Path, api: str) -> None:
    tree = _tree(tmp_path / "ext", api)
    with pytest.raises(SystemExit, match="make gen-deployment api=https://"):
        package(tree, tmp_path / "out")
    assert not (tmp_path / "out").exists() or not list((tmp_path / "out").iterdir())


def test_a_local_qa_zip_may_be_insecure_and_says_so_loudly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tree = _tree(tmp_path / "ext", "http://10.11.9.25:8088/api")
    assert package(tree, tmp_path / "out", allow_insecure=True).exists()
    assert "INSECURE" in capsys.readouterr().err


def test_the_real_extension_packages_with_what_it_needs_to_run(tmp_path: Path) -> None:
    # The tree's own deployment is a local QA one; this checks the file list.
    built = package(EXTENSION, tmp_path, allow_insecure=True)
    with zipfile.ZipFile(built) as archive:
        names = set(archive.namelist())
        manifest = json.loads(archive.read("manifest.json"))
    assert "key" not in manifest
    assert manifest["background"]["service_worker"] in names
    assert manifest["side_panel"]["default_path"] in names
    assert manifest["options_page"] in names
    assert not [n for n in names if ".test." in n or "test-support" in n or "fixtures" in n]
    assert not [n for n in names if n.startswith("src/page/")]
    assert "src/background/deployment.generated.js" in names
