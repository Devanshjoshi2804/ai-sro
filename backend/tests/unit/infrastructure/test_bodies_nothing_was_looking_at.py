"""Bodies the credential removal never opened.

It handled JSON and form-encoded and returned everything else untouched, so a
WMS that speaks SOAP had its `<Password>` written to the evidence store exactly
as sent, and a multipart login form kept the operator's password in the part
that carried it. JSON had a hole of its own: a credential was only removed when
its value was a scalar, and `{"password": ["hunter2"]}` -- which is what an HTML
form with a repeated field produces -- went in verbatim while the capture
reported nothing removed.
"""

from __future__ import annotations

from sro.infrastructure.steel.redaction import REDACTED, redact_body


def test_a_credential_in_a_list_is_still_a_credential() -> None:
    body, removed = redact_body('{"password": ["hunter2"], "user": "clerk"}', content_type="json")

    assert "hunter2" not in body
    assert removed == ("password",)
    assert "clerk" in body, "and the rest of the demonstration is untouched"


def test_a_soap_password_element_is_removed() -> None:
    envelope = (
        "<soapenv:Envelope><soapenv:Body><Login>"
        "<Username>clerk</Username><Password>hunter2</Password>"
        "</Login></soapenv:Body></soapenv:Envelope>"
    )

    body, removed = redact_body(envelope, content_type="text/xml; charset=utf-8")

    assert "hunter2" not in body
    assert "clerk" in body
    assert removed == ("Password",)


def test_a_credential_in_an_xml_attribute_too() -> None:
    body, removed = redact_body(
        '<Login user="clerk" password="hunter2"/>', content_type="application/xml"
    )

    assert "hunter2" not in body and REDACTED in body
    assert removed == ("password",)


def test_a_multipart_login_loses_the_part_that_carried_the_password() -> None:
    form = (
        "--X\r\n"
        'Content-Disposition: form-data; name="username"\r\n'
        "\r\n"
        "clerk\r\n"
        "--X\r\n"
        'Content-Disposition: form-data; name="password"\r\n'
        "\r\n"
        "hunter2\r\n"
        "--X--\r\n"
    )

    body, removed = redact_body(form, content_type="multipart/form-data; boundary=X")

    assert "hunter2" not in body
    assert "clerk" in body
    assert removed == ("password",)


def test_a_body_in_no_shape_it_knows_is_left_exactly_as_it_was() -> None:
    """Mangling evidence is its own fault. What it cannot read, it keeps."""
    opaque = "\x00\x01binary-ish"

    assert redact_body(opaque, content_type="application/octet-stream") == (opaque, ())
