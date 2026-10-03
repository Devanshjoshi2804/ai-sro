"""ONE secret-name rule (sensitivity.py), generated into the browser: one corpus, same answers."""

from __future__ import annotations

import json
import re
import shutil
import subprocess

import pytest

from sro.domain.observation.redaction import is_secret_name
from sro.domain.recording.sensitivity import is_secret_field, is_text_entry
from sro.infrastructure.steel.generate_extension_recorder import (
    PAGE_CODE_OUT,
    sensitivity_module_source,
)

HIDDEN = [
    "Password", "pwd", "Login code", "Enter your login code", "One-time code", "OTP",
    "Passcode", "API key", "Access token", "user_login_code", "loginCode",
    "send_one_time_code", "enter_login_code", "Verification code", "security code",
    "secret key", "Session ID", "refreshToken", "j_password",
]  # fmt: skip
CAPTURABLE = [
    "Pick session id", "Work session id", "Count session ID", "Login code type",
    "Login code expiry", "Dock access key", "Customer type code", "Code",
    "Verification status", "Postal code", "Dock door code", "shippingNotes",
    "passenger_count", "clientId", "",
]  # fmt: skip
CORPUS = HIDDEN + CAPTURABLE
# (role, tag, editable): D-OTP, a name judges only a control a person types text into.
CONTROLS = [
    ("textbox", "input", False), ("textbox", "textarea", False), (None, "input", False),
    (None, "textarea", False), (None, "div", True), ("textbox", "div", False),
    ("searchbox", "div", False), ("checkbox", "input", False), ("radio", "input", False),
    ("switch", "button", False), ("combobox", "select", False), (None, "select", False),
    ("combobox", "input", False), ("listbox", "div", False), ("button", "input", False),
    ("slider", "input", False), (None, "div", False), ("checkbox", "div", True),
]  # fmt: skip
ENTRY = [True] * 7 + [False] * 5 + [True] + [False] * 5  # a typed-into combobox is text
RETURN = "\nreturn { isSecretName, isTextEntry };"

NODE = shutil.which("node") or "node"
pytestmark = pytest.mark.skipif(NODE == "node", reason="node is not installed")


def _node(program: str) -> list[bool]:
    done = subprocess.run(  # noqa: S603
        [NODE, "--input-type=module", "-e", program],
        capture_output=True, text=True, check=True, timeout=60,
    )  # fmt: skip
    return json.loads(done.stdout)


def test_the_corpus_is_judged_as_written() -> None:
    assert all(is_secret_field(name) for name in HIDDEN)
    assert not any(is_secret_field(name) for name in CAPTURABLE)


def test_the_server_redacts_request_keys_as_the_page_hides_fields() -> None:
    assert [is_secret_name(n) for n in CORPUS] == [is_secret_field(n) for n in CORPUS]


def test_the_generated_module_answers_as_python_does() -> None:
    program = (
        "const m = 'data:text/javascript,' + encodeURIComponent("
        + json.dumps(sensitivity_module_source())
        + "); const { isSecretName } = await import(m);"
        + f"console.log(JSON.stringify({json.dumps(CORPUS)}.map(isSecretName)));"
    )
    assert _node(program) == [is_secret_field(n) for n in CORPUS]


def test_the_page_codes_generated_region_answers_as_python_does() -> None:
    source = PAGE_CODE_OUT.read_text(encoding="utf-8")
    region = re.search(
        r"// BEGIN generated secret-name rule.*?// END generated secret-name rule", source, re.S
    )
    assert region, "page-code.js lost its generated secret-name region"
    program = (
        f"const {{ isSecretName }} = new Function({json.dumps(region.group(0) + RETURN)})();"
        + f"console.log(JSON.stringify({json.dumps(CORPUS)}.map(isSecretName)));"
    )
    assert _node(program) == [is_secret_field(n) for n in CORPUS]


def test_only_a_text_entry_control_is_judged_by_its_name() -> None:
    assert [is_text_entry(*c) for c in CONTROLS] == ENTRY


def test_the_page_codes_control_kind_answers_as_python_does() -> None:
    source = PAGE_CODE_OUT.read_text(encoding="utf-8")
    region = re.search(
        r"// BEGIN generated secret-name rule.*?// END generated secret-name rule", source, re.S
    )
    assert region
    program = (
        f"const {{ isTextEntry }} = new Function({json.dumps(region.group(0) + RETURN)})();"
        + f"console.log(JSON.stringify({json.dumps(CONTROLS)}.map((c) => isTextEntry(...c))));"
    )
    assert _node(program) == ENTRY


def test_page_code_keeps_one_word_list() -> None:
    source = PAGE_CODE_OUT.read_text(encoding="utf-8")
    assert source.count("SECRET_WORDS = new Set(") == 1
