"""CDP shapes are the part most likely to move under a Chrome upgrade.

These tests use payloads shaped exactly as the protocol emits them, so a shape
change fails here rather than silently producing an empty recording.
"""

from __future__ import annotations

from sro.application.capture.decode import (
    epoch_to_datetime,
    to_ax_graph,
    to_console_message,
    to_cookies,
    to_headers,
    to_initiator,
    to_input_action,
    to_page_event,
    to_timing,
)
from sro.domain.recording.events import ActionKind
from sro.domain.recording.network import InitiatorKind
from sro.domain.recording.state import ConsoleLevel, PageEventKind
from tests import factories as f


class TestHeaders:
    def test_every_header_survives_including_secrets(self) -> None:
        raw = {"Authorization": "Bearer live-token", "X-Facility": "DC01"}

        assert to_headers(raw) == raw

    def test_absent_headers_are_an_empty_mapping_not_an_error(self) -> None:
        assert to_headers(None) == {}


class TestInitiator:
    def test_the_js_stack_is_kept(self) -> None:
        initiator = to_initiator(
            {
                "type": "script",
                "stack": {
                    "callFrames": [
                        {
                            "functionName": "onRelease",
                            "url": "https://wms.test/app.js",
                            "lineNumber": 42,
                            "columnNumber": 7,
                        }
                    ]
                },
            }
        )

        assert initiator is not None
        assert initiator.kind is InitiatorKind.SCRIPT
        assert initiator.stack[0].function == "onRelease"
        assert initiator.stack[0].line == 42

    def test_an_unknown_type_degrades_rather_than_raises(self) -> None:
        initiator = to_initiator({"type": "something-new-in-chrome"})

        assert initiator is not None
        assert initiator.kind is InitiatorKind.OTHER


class TestTiming:
    def test_phases_that_did_not_happen_are_none_not_zero(self) -> None:
        # A reused connection has no DNS or TLS phase; CDP reports -1.
        timing = to_timing(
            {
                "dnsStart": -1,
                "dnsEnd": -1,
                "sendStart": 10.0,
                "sendEnd": 12.0,
                "receiveHeadersEnd": 30.0,
            }
        )

        assert timing is not None
        assert timing.dns_ms is None
        assert timing.send_ms == 2.0
        assert timing.wait_ms == 18.0


class TestCookies:
    def test_attributes_that_decide_replayability_are_kept(self) -> None:
        cookies = to_cookies(
            [
                {
                    "name": "session",
                    "value": "abc",
                    "domain": "wms.test",
                    "path": "/",
                    "secure": True,
                    "httpOnly": True,
                    "sameSite": "Strict",
                    "expires": -1,
                }
            ]
        )

        assert len(cookies) == 1
        assert cookies[0].http_only is True
        assert cookies[0].same_site == "Strict"
        assert cookies[0].expires is None


class TestAxGraph:
    def test_the_parent_chain_survives_ignored_nodes(self) -> None:
        payload = {
            "nodes": [
                {
                    "nodeId": "1",
                    "role": {"value": "dialog"},
                    "name": {"value": "Release"},
                    "childIds": ["2"],
                },
                {
                    "nodeId": "2",
                    "parentId": "1",
                    "role": {"value": "generic"},
                    "ignored": True,
                    "childIds": ["3"],
                },
                {
                    "nodeId": "3",
                    "parentId": "2",
                    "role": {"value": "button"},
                    "name": {"value": "Save"},
                    "properties": [{"name": "disabled", "value": {"value": True}}],
                },
            ]
        }

        graph = to_ax_graph(payload, url="https://wms.test", taken_at=f.at(0))
        button = graph.node("3")

        assert button is not None
        assert "disabled" in button.states
        assert graph.path(button).endswith("button “Save”")
        assert graph.root_id == "1"


class TestConsole:
    def test_a_logged_validation_failure_keeps_its_text_and_origin(self) -> None:
        message = to_console_message(
            {
                "type": "error",
                "args": [{"value": "quantity exceeds available stock"}],
                "stackTrace": {
                    "callFrames": [
                        {
                            "functionName": "validate",
                            "url": "https://wms.test/app.js",
                            "lineNumber": 9,
                            "columnNumber": 1,
                        }
                    ]
                },
            },
            at=f.at(0),
        )

        assert message.level is ConsoleLevel.ERROR
        assert "exceeds available stock" in message.text
        assert message.url == "https://wms.test/app.js"


class TestPageEvents:
    def test_a_navigation_is_recognised(self) -> None:
        event = to_page_event(
            "Page.frameNavigated", {"frame": {"url": "https://wms.test/orders"}}, at=f.at(0)
        )

        assert event is not None
        assert event.kind is PageEventKind.NAVIGATED
        assert event.url == "https://wms.test/orders"

    def test_an_unmapped_method_is_dropped_rather_than_guessed(self) -> None:
        assert to_page_event("Page.lifecycleEvent", {}, at=f.at(0)) is None


class TestInputAction:
    def test_the_recorder_payload_becomes_an_action_with_its_selectors(self) -> None:
        action = to_input_action(
            {
                "kind": "click",
                "value": None,
                "modifiers": ["shift"],
                "target": {
                    "tag": "button",
                    "name": "Release",
                    "testId": "release-btn",
                    "cssPath": "form > button.primary",
                    "xpath": "/html[1]/body[1]/form[1]/button[1]",
                    "bounds": {"x": 10, "y": 20, "width": 100, "height": 40},
                    "attributes": {"type": "submit"},
                },
            }
        )

        assert action.kind is ActionKind.CLICK
        assert action.modifiers == frozenset({"shift"})
        assert action.target is not None
        assert action.target.test_id == "release-btn"
        assert action.target.bounds is not None
        assert action.target.bounds.width == 100


def test_wall_clock_timestamps_are_timezone_aware() -> None:
    assert epoch_to_datetime(1_772_000_000.0).tzinfo is not None
