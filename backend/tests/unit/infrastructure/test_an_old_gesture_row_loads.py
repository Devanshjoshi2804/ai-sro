from pydantic import TypeAdapter

from sro.domain.observation.gesture import Action, PageMark

OLD_ROW = {
    "kind": "click",
    "at": 1_790_000_000.0,
    "value": None,
    "secret": False,
    "url": "https://wms.example/a",
    "target": {
        "tag": "button",
        "role": "button",
        "name": "Save",
        "secret": False,
        "text": "Save",
        "test_id": None,
        "css_path": "button",
        "xpath": "/html/body/button[1]",
        "required": None,
        "component": None,
        "bounds": {},
        "attributes": {},
        "landmarks": [],
    },
    "modifiers": [],
    "frame_path": None,
    "detail": 1,
    "trusted": True,
    "after": None,
    "outlines": [],
}


def test_a_row_stored_before_the_new_fields_loads_with_their_defaults() -> None:
    action = TypeAdapter(Action).validate_python(OLD_ROW)
    assert (action.place, action.effect, action.choice) == (None, None, None)
    assert action.target is not None
    assert (action.target.label_text, action.target.sibling_index, action.target.full_name) == (
        None,
        None,
        None,
    )


def test_an_old_page_mark_loads_with_no_cookies_and_no_mail_thread() -> None:
    mark = TypeAdapter(PageMark).validate_python({"at": 1.0, "page_kind": "navigated"})
    assert (mark.cookies, mark.mail_thread) == ((), None)
