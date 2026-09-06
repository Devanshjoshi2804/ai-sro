from sro.domain.observation.gesture import Action, Component, Gesture, Target, new_gesture_id


def test_a_gesture_id_has_the_rig_shape() -> None:
    assert new_gesture_id().startswith("ges_") and len(new_gesture_id()) == 36


def test_the_domain_gesture_is_built_from_parts_and_the_parts_are_frozen() -> None:
    action = Action(
        kind="type",
        at=1.0,
        value="ACME-4471",
        target=Target(name="Client Code", component=Component(item_id="clientCode")),
    )
    g = Gesture(
        id="ges_1",
        tenant="acme",
        stream_id="s",
        batch_id="b",
        at=1.0,
        url=None,
        system="http://127.0.0.1:63319",
        tab_id=1,
        frame_url=None,
        action=action,
    )
    assert g.action.target and g.action.target.component
    assert g.action.target.component.item_id == "clientCode"
    try:
        action.value = "x"  # type: ignore[misc]
    except AttributeError:
        pass
    else:
        raise AssertionError("an action changed after the fact")
