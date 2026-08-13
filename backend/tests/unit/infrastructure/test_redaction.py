"""Credentials never reach storage.

Everything else a demonstration does is kept verbatim. A password is the one
exception: it is not evidence of what happened, it is a key to the customer's
system, and an evidence store holding keys is a credential store nobody agreed
to run.
"""

from __future__ import annotations

import json

import pytest

from sro.domain.recording.element import ElementFingerprint
from sro.domain.recording.events import ActionKind, InputAction
from sro.domain.recording.sensitivity import is_secret_field
from sro.domain.shared.errors import InvariantViolation
from sro.infrastructure.steel.redaction import REDACTED, redact_body


class TestBodies:
    def test_a_login_post_loses_its_password_and_says_so(self) -> None:
        body = json.dumps({"username": "clerk", "password": "hunter2", "facility": "DC01"})

        cleaned, removed = redact_body(body, content_type="application/json")
        document = json.loads(cleaned)

        assert document["password"] == REDACTED
        assert removed == ("password",)
        # Everything that is not a credential is still there, verbatim.
        assert document["username"] == "clerk"
        assert document["facility"] == "DC01"

    def test_form_encoded_logins_too(self) -> None:
        cleaned, removed = redact_body(
            "user=clerk&passwd=hunter2&facility=DC01",
            content_type="application/x-www-form-urlencoded",
        )

        assert "hunter2" not in cleaned
        assert "clerk" in cleaned
        assert removed == ("passwd",)

    def test_nested_credentials_are_found(self) -> None:
        body = json.dumps({"auth": {"apiKey": "sk-live-1234"}, "lines": [{"sku": "A-1"}]})

        cleaned, removed = redact_body(body, content_type="application/json")

        assert "sk-live-1234" not in cleaned
        assert removed == ("apiKey",)
        assert "A-1" in cleaned, "business data must survive"

    def test_a_business_body_is_returned_untouched(self) -> None:
        body = json.dumps({"sku": "SKU-4471", "quantity": 124, "reason": "cycle count"})

        cleaned, removed = redact_body(body, content_type="application/json")

        assert cleaned == body
        assert removed == ()

    def test_an_unparseable_body_is_left_alone_rather_than_mangled(self) -> None:
        cleaned, removed = redact_body("<xml>not json</xml>", content_type="application/xml")

        assert cleaned == "<xml>not json</xml>"
        assert removed == ()

    @pytest.mark.parametrize(
        "field",
        ["password", "passwd", "user_password", "apiKey", "api_key", "otp", "pin", "cvv", "token"],
    )
    def test_the_names_credentials_actually_use(self, field: str) -> None:
        assert is_secret_field(field)

    @pytest.mark.parametrize("field", ["sku", "quantity", "location", "passenger_count"])
    def test_business_field_names_are_not_credentials(self, field: str) -> None:
        assert not is_secret_field(field)


FIELD = ElementFingerprint(tag="input", accessible_name="Password", css_path="form > input")


class TestTypedValues:
    def test_a_secret_input_cannot_carry_its_value(self) -> None:
        with pytest.raises(InvariantViolation, match="must not carry its value"):
            InputAction(kind=ActionKind.TYPE, target=FIELD, value="hunter2", secret=True)

    def test_a_secret_input_is_valid_without_one(self) -> None:
        action = InputAction(kind=ActionKind.TYPE, target=FIELD, secret=True)

        assert action.value is None
        assert action.secret is True
