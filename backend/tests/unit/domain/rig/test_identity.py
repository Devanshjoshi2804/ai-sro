import pytest

from sro.domain.observation.gesture import Action, Gesture
from sro.domain.observation.identity import (
    K_MIN_SHARED_STEPS,
    K_SAME_JOB,
    named_alike,
    resolve,
    screen_of,
    shape_key,
)
from sro.domain.skill.workflow import Step, Workflow


def _workflow(cites: list[str], shape: list[list[str]], **over: object) -> Workflow:
    base: dict[str, object] = {
        "id": "wfl_x",
        "tenant": "acme",
        "title": "a job",
        "narrative": "",
        "systems": ["https://wms.example"],
        "steps": [
            Step(order=i, says="x", system="https://wms.example", cites=[c])
            for i, c in enumerate(cites)
        ],
        "shape_key": shape,
    }
    return Workflow(**{**base, **over})


SHAPE = [
    ["https://wms.example", "clientCode", "type"],
    ["https://wms.example", "saveButton", "click"],
]


def test_nothing_known_means_a_new_job() -> None:
    assert resolve(_workflow(["ges_1"], SHAPE), []).kind == "new"


def test_the_same_evidence_again_is_the_same_occurrence() -> None:
    """Mining re-runs over evidence it has already read. A key that answered
    differently on a second pass would breed a workflow that can never pair."""
    known = _workflow(["ges_1", "ges_2"], SHAPE, id="wfl_known")
    again = _workflow(["ges_1", "ges_2"], SHAPE)

    resolution = resolve(again, [known])

    assert resolution.kind == "same_occurrence"
    assert resolution.workflow_id == "wfl_known"


def test_the_same_job_on_wholly_different_evidence_is_recognised() -> None:
    """This is the question ids cannot answer: two occurrences cite disjoint
    gestures, so overlap between them is zero by construction."""
    known = _workflow(["ges_1", "ges_2"], SHAPE, id="wfl_known")
    tuesday = _workflow(["ges_90", "ges_91"], SHAPE)

    resolution = resolve(tuesday, [known])

    assert resolution.kind == "same_job"
    assert resolution.workflow_id == "wfl_known"
    assert resolution.score >= K_SAME_JOB


def test_a_different_job_sharing_one_lookup_is_not_folded_in() -> None:
    """Containment divides by the smaller shape, so a two-step job is half
    contained by anything sharing one step. A ratio cannot tell "half of two"
    from "half of twenty"; the overlap has to be real in absolute terms too."""
    known = _workflow(["ges_1"], SHAPE, id="wfl_known")
    other = _workflow(
        ["ges_50"],
        [["https://wms.example", "clientCode", "type"]]
        + [["https://sap.example", f"field{n}", "type"] for n in range(8)],
    )

    assert resolve(other, [known]).kind == "new"


def test_a_small_job_inside_a_big_one_is_the_same_job_and_says_which_contains() -> None:
    big = _workflow(
        ["ges_1"],
        SHAPE + [["https://sap.example", f"f{n}", "click"] for n in range(6)],
        id="wfl_big",
    )
    small = _workflow(["ges_70"], SHAPE)

    resolution = resolve(small, [big])

    assert resolution.kind == "same_job"
    assert resolution.contains is False


def test_a_workflow_with_no_shape_is_new_rather_than_a_match() -> None:
    known = _workflow(["ges_1"], SHAPE, id="wfl_known")

    assert resolve(_workflow(["ges_9"], []), [known]).kind == "new"


def test_one_cited_gesture_in_common_is_not_a_re_read() -> None:
    """The two layers, told apart. Jaccard on ids says 1-in-10 is not the same
    window; containment on the same ids would say 1.0 and call it a re-read.
    Which layer answers is the whole of this module, so a test that passes
    under either measure tests nothing."""
    known = _workflow([f"ges_{n}" for n in range(10)], SHAPE, id="wfl_known")
    sliver = _workflow(["ges_0"], SHAPE)

    resolution = resolve(sliver, [known])

    assert resolution.kind == "same_job"
    assert resolution.score == 1.0


def test_the_measured_overlap_is_reported_not_assumed() -> None:
    """Three citations of four is the same occurrence and is not identity. A
    flat 1.0 is a number no caller can threshold on twice."""
    known = _workflow(["ges_1", "ges_2", "ges_3"], SHAPE, id="wfl_known")
    again = _workflow(["ges_1", "ges_2", "ges_3", "ges_4"], SHAPE)

    resolution = resolve(again, [known])

    assert resolution.kind == "same_occurrence"
    assert resolution.score == 0.75


def test_the_closest_evidence_match_wins_not_the_first_listed() -> None:
    partial = _workflow(["ges_1", "ges_2", "ges_3"], SHAPE, id="wfl_partial")
    exact = _workflow(["ges_1", "ges_2", "ges_3", "ges_4"], SHAPE, id="wfl_exact")
    again = _workflow(["ges_1", "ges_2", "ges_3", "ges_4"], SHAPE)

    resolution = resolve(again, [partial, exact])

    assert resolution.workflow_id == "wfl_exact"
    assert resolution.score == 1.0


def test_a_real_match_is_not_masked_by_a_higher_scoring_stub() -> None:
    """A one-step stub is 1.0-contained by anything that begins where it does.
    Take the best of what clears both bars, not the best overall and then the
    bars -- otherwise the stub wins the comparison, fails the step count, and
    the genuine match standing behind it is never reached."""
    proposal = _workflow(["ges_1"], [*SHAPE, ["https://sap.example", "post", "click"]])
    stub = _workflow(["ges_2"], SHAPE[:1], id="wfl_stub")
    real = _workflow(
        ["ges_3"],
        SHAPE + [["https://sap.example", f"other{n}", "type"] for n in range(2)],
        id="wfl_real",
    )

    resolution = resolve(proposal, [stub, real])

    assert resolution.kind == "same_job"
    assert resolution.workflow_id == "wfl_real"
    assert resolution.score == pytest.approx(2 / 3)


def test_exactly_the_minimum_shared_steps_at_exactly_the_threshold_matches() -> None:
    """Both bars are sat on at once: containment is exactly K_SAME_JOB and the
    shared count is exactly K_MIN_SHARED_STEPS. Either comparison written `>`
    instead of `>=` refuses this."""
    shared = [["https://wms.example", f"shared{n}", "type"] for n in range(K_MIN_SHARED_STEPS)]
    known = _workflow(
        ["ges_1"],
        shared + [["https://sap.example", f"theirs{n}", "click"] for n in range(2)],
        id="wfl_known",
    )
    mine = _workflow(
        ["ges_9"],
        shared + [["https://sap.example", f"mine{n}", "click"] for n in range(2)],
    )

    resolution = resolve(mine, [known])

    assert resolution.kind == "same_job"
    assert resolution.score == K_SAME_JOB


def test_another_tenants_workflow_is_never_the_same_thing() -> None:
    """Same shape, same citations, different customer. known_workflows() scopes
    its query by tenant; resolve() takes whatever list it is handed, and welding
    one tenant's job onto another's is not a mistake you can undo."""
    theirs = _workflow(["ges_1", "ges_2"], SHAPE, id="wfl_theirs", tenant="globex")
    mine = _workflow(["ges_1", "ges_2"], SHAPE)

    assert resolve(mine, [theirs]).kind == "new"


def test_two_shared_steps_out_of_five_is_not_enough_of_the_job() -> None:
    """The mirror of the one-shared-lookup case, and the reason both bars are
    needed rather than either. There the ratio passed and the count refused;
    here the count passes -- two steps really are shared -- and the ratio
    refuses, because two steps of a five-step job is not that job."""
    shared = [["https://wms.example", f"shared{n}", "type"] for n in range(K_MIN_SHARED_STEPS)]
    known = _workflow(
        ["ges_1"],
        shared + [["https://sap.example", f"theirs{n}", "click"] for n in range(3)],
        id="wfl_known",
    )
    mine = _workflow(
        ["ges_9"],
        shared + [["https://sap.example", f"mine{n}", "click"] for n in range(3)],
    )

    assert resolve(mine, [known]).kind == "new"


def test_the_closest_shape_match_wins_not_the_last_one_that_qualified() -> None:
    """Two knowns can both clear both bars. The one the proposal actually is
    has to win, whatever order the store handed them over in."""
    proposal = _workflow(["ges_1"], [*SHAPE, ["https://sap.example", "post", "click"]])
    exact = _workflow(["ges_2"], [*SHAPE, ["https://sap.example", "post", "click"]], id="wfl_exact")
    looser = _workflow(
        ["ges_3"],
        SHAPE + [["https://sap.example", f"other{n}", "type"] for n in range(2)],
        id="wfl_looser",
    )

    resolution = resolve(proposal, [exact, looser])

    assert resolution.workflow_id == "wfl_exact"
    assert resolution.score == 1.0


KEYCLOAK = "https://keycloak-service-exec-wms-keycloak-prod.us.live.external.byp.ai"
MAIL = "https://mail.google.com"
WMS = "https://bf56-kms-wms-web-np2.jdadelivers.com"


def test_a_doing_of_one_distinct_step_does_not_fold_into_a_bigger_job() -> None:
    """A shape is a SET, so a doing that touches one control twice is one
    entry wide, and "every step of it is in that job" is then true of any
    job that touches that control -- at 1.0. Folding on it placed the doing's
    gestures under the wrong job for good. One entry is not enough to say
    which job this is; it resolves new."""
    stored = _workflow(
        ["ges_a", "ges_b", "ges_c"],
        [
            [KEYCLOAK, "name|Username or email", "type"],
            [KEYCLOAK, "anon|click", "click"],
            [KEYCLOAK, "anon|type", "type"],
        ],
        id="wfl_stored",
    )
    again = _workflow(
        ["ges_d", "ges_e"],
        [
            [KEYCLOAK, "name|Username or email", "type"],
            [KEYCLOAK, "name|Username or email", "type"],
        ],
    )

    assert resolve(again, [stored]).kind == "new"


def test_a_sign_in_that_does_one_thing_twice_folds_by_what_it_signs_in_to() -> None:
    """Measured on the deployment 2026-09-19: three `Log in to Keycloak`, one
    of them the same box typed twice. The shape cannot say which job that is;
    the sign-in can -- the same credential host, the same application after."""
    stored = _workflow(
        ["ges_a", "ges_b", "ges_c"],
        [
            [KEYCLOAK, "name|Username or email", "type"],
            [KEYCLOAK, "anon|click", "click"],
            [KEYCLOAK, "anon|type", "type"],
        ],
        id="wfl_stored",
        signs_in=True,
    )
    again = _workflow(
        ["ges_d", "ges_e"],
        [[KEYCLOAK, "name|Username or email", "type"]] * 2,
        signs_in=True,
    )
    lands = {"wfl_stored": (KEYCLOAK, WMS), again.id: (KEYCLOAK, WMS)}

    assert resolve(again, [stored], signs_in_to=lands).workflow_id == "wfl_stored"


def test_a_step_nobody_could_name_matches_the_named_one_it_is() -> None:
    """`target_identity` falls back to `anon|click` when a recording gives it
    nothing to work with, and whether it has anything to work with is a property
    of that recording, not of the job.

    Measured 2026-09-19: two `Reply to Email` three hours apart, identical but
    for the first step -- `link|Reply` in one reading, `anon|click` in the
    other. The overlap was the Send button alone, one step, under the bar.
    """
    stored = _workflow(
        ["ges_a", "ges_b"],
        [[MAIL, "link|Reply", "click"], [MAIL, "button|Send", "click"]],
        id="wfl_stored",
    )
    again = _workflow(
        ["ges_c", "ges_d"],
        [[MAIL, "anon|click", "click"], [MAIL, "button|Send", "click"]],
    )

    assert resolve(again, [stored]).kind == "same_job"


def test_an_unnamed_step_matches_one_named_step_and_not_two() -> None:
    """Otherwise a pair of anonymous clicks on one system would claim every
    named click on it, and two unrelated jobs would be one."""
    stored = _workflow(
        ["ges_a", "ges_b"],
        [[MAIL, "link|Reply", "click"], [MAIL, "button|Send", "click"]],
        id="wfl_stored",
    )
    mystery = _workflow(
        ["ges_c", "ges_d", "ges_e"],
        [
            [MAIL, "anon|click", "click"],
            [MAIL, "anon|click", "click"],
            [MAIL, "link|Archive", "click"],
        ],
    )

    # One anonymous entry after the set collapse, so exactly one named step is
    # claimable -- and this proposal has a step of its own that is nowhere in
    # the stored job.
    assert resolve(mystery, [stored]).kind == "new"


def test_a_job_is_not_folded_into_one_that_shares_a_single_generic_click() -> None:
    """The trap the absolute bar exists for, and it is not hypothetical.

    `Navigate to Receiving` on the deployment is one `tabItem` click repeated
    three times -- one distinct entry, and `tabItem` is the component id of
    every tab on that system. Scaling the bar down to the smaller shape folded
    a two-step `Navigate to Warehouse Sub-menu` into it on the strength of that
    one click. The shape keeps them apart, whatever they are called.
    """
    generic = _workflow(
        ["ges_a", "ges_b", "ges_c"],
        [[WMS, "tabItem", "click"], [WMS, "tabItem", "click"], [WMS, "tabItem", "click"]],
        id="wfl_generic",
    )
    other = _workflow(
        ["ges_d", "ges_e"],
        [[WMS, "toolbar button", "click"], [WMS, "tabItem", "click"]],
    )

    assert resolve(other, [generic]).kind == "new"


def test_a_one_step_stored_job_does_not_swallow_a_bigger_doing() -> None:
    """A stored job one entry wide -- and that entry an unnamed click -- is
    present in every doing that clicks anything on its screen. Folding and
    growing on that would replace the job with whatever came next."""
    stub = _workflow(
        ["ges_a"], [[WMS, "anon|button", "click"]], id="wfl_stub", title="Open Receiving"
    )
    bigger = _workflow(
        ["ges_b", "ges_c", "ges_d"],
        [[WMS, "dateField", "type"], [WMS, "exportButton", "click"], [WMS, "asnNumber", "type"]],
        title="Open Receiving and Export ASN",
    )

    assert resolve(bigger, [stub]).kind == "new"


def test_a_lookup_two_jobs_begin_with_still_does_not_join_them() -> None:
    """The original argument for the bar, unchanged."""
    mine = _workflow(
        [f"ges_m{n}" for n in range(4)],
        [[WMS, "lookup", "type"]] + [[WMS, f"mine{n}", "click"] for n in range(3)],
    )
    theirs = _workflow(
        [f"ges_t{n}" for n in range(4)],
        [[WMS, "lookup", "type"]] + [[WMS, f"theirs{n}", "click"] for n in range(3)],
        id="wfl_theirs",
    )

    assert resolve(mine, [theirs]).kind == "new"


def test_an_unnamed_step_is_not_aliased_across_systems_or_kinds() -> None:
    """`anon|click` says "a click here we could not name", and the here and the
    click are the rest of what it says. A rule that dropped either would match
    a click in a mailbox to a Save in a warehouse."""
    stored = _workflow(
        ["ges_a", "ges_b"],
        [[WMS, "saveButton", "click"], [WMS, "clientCode", "type"]],
        id="wfl_stored",
    )
    elsewhere = _workflow(
        ["ges_c", "ges_d"],
        [[MAIL, "anon|click", "click"], [WMS, "clientCode", "type"]],
    )
    wrong_kind = _workflow(
        ["ges_e", "ges_f"],
        [[WMS, "anon|type", "type"], [WMS, "anon|press", "press"]],
    )

    assert resolve(elsewhere, [stored]).kind == "new", "a click elsewhere is not that click"
    assert resolve(wrong_kind, [stored]).kind == "new", "typing is not clicking"


def test_the_score_counts_the_same_shared_steps_the_bar_does() -> None:
    """Two gates that disagree about what a shared step is are one gate.

    Here the raw set intersection is one entry of three -- 0.33, under
    K_SAME_JOB -- while every step of the proposal is in fact present in the
    stored job, two of them under names this recording could not read. Scored
    the raw way the job is refused and mined again as a duplicate, which is the
    whole failure being repaired.
    """
    stored = _workflow(
        ["ges_a", "ges_b", "ges_c"],
        [
            [MAIL, "link|Reply", "click"],
            [MAIL, "textbox|Message Body", "type"],
            [MAIL, "button|Send", "click"],
        ],
        id="wfl_stored",
    )
    again = _workflow(
        ["ges_d", "ges_e", "ges_f"],
        [
            [MAIL, "anon|click", "click"],
            [MAIL, "anon|type", "type"],
            [MAIL, "button|Send", "click"],
        ],
    )

    resolution = resolve(again, [stored])

    assert resolution.kind == "same_job"
    assert resolution.score == 1.0, "every step of it is in that job"


# -- the screen is part of what a job IS --------------------------------------
#
# Measured on the deployment 2026-09-21, on an operator's own demonstration.
# They did `Create a Transport Equipment Type` three times, cleanly. The miner
# read it correctly -- "steps 1-6 are done once per thing" -- and then:
#
#     Create a Transport Equipment Type: recognised as a job already stored
#     -- wfl_4869… at 0.50
#
# `wfl_4869…` is `Create a Warehouse Equipment Type`. A different screen of
# the same application. Nothing was learnt from three good demonstrations, and
# a parameter was widened on the wrong job.
#
# The shape held `gesture.system`, which is an ORIGIN, and an origin is not a
# screen in a single-page application: every config screen in this WMS is
# `bf56-kms-wms-web-np2.jdadelivers.com` and the screen is in the fragment.
# What was left to tell two jobs apart was the widget choreography, and every
# config screen in the product has the same one -- click a tab, click Add,
# type, type, click Save. The store held 13 screens across 2 origins; the key
# could see the 2.


PORTAL = "https://bf56-kms-wms-web-np2.jdadelivers.com/portal"
TRANSPORT = f"{PORTAL}?siteId=SG#wm.config/wm.config.equipment.equipment.transportequipmenttype////"
WAREHOUSE = f"{PORTAL}?siteId=SG#wm.config/wm.config.equipment.equipment.warehouseequipmenttype////"


def _on(page: str, kind: str = "click") -> Gesture:
    return Gesture(
        id=f"ges_{abs(hash((page, kind)))}",
        tenant="acme",
        stream_id="str_1",
        batch_id="bat_1",
        at=1.0,
        url=f"{PORTAL}/page?libraryContext=abc&siteId=SG",
        system="https://bf56-kms-wms-web-np2.jdadelivers.com",
        tab_id=1,
        frame_url=None,
        page_url=page,
        action=Action(kind=kind, at=1.0),
    )


def test_two_screens_of_one_application_are_two_jobs() -> None:
    assert screen_of(_on(TRANSPORT)) != screen_of(_on(WAREHOUSE))
    # And the shapes that follow from them share nothing, where before they
    # shared everything: same origin, same control, same action.
    mine = set(shape_key([_on(TRANSPORT), _on(TRANSPORT, "type")]))
    theirs = set(shape_key([_on(WAREHOUSE), _on(WAREHOUSE, "type")]))
    assert not (mine & theirs)


def test_the_same_screen_in_two_sessions_is_one_job() -> None:
    """The other direction, and the worse failure if it were wrong. `siteId` is
    which warehouse somebody signed in to and the trailing `////` are empty
    positional segments; both move between two doings of one job, and a screen
    that changed per doing would make every doing a new job."""
    monday = _on(TRANSPORT)
    tuesday = _on(TRANSPORT.replace("siteId=SG", "siteId=BLR1").replace("////", "//"))

    assert screen_of(monday) == screen_of(tuesday)


def test_a_gesture_in_a_frame_is_placed_by_the_tab_it_is_in() -> None:
    """`page_url` and not `url`: a gesture inside an iframe reports the frame's
    src, and the frame is not the screen. The fixture's `url` is the portal's
    inner page, which is the same string on every screen there is."""
    inside = _on(TRANSPORT)

    assert "transportequipmenttype" in screen_of(inside)


def test_a_page_with_no_route_in_it_is_still_a_screen() -> None:
    """Most of the web. The path is the screen, and a query is not part of it."""
    plain = _on("https://mail.google.com/mail/u/0/?tab=rm&ogbl#sent")

    assert screen_of(plain) == "https://mail.google.com/mail/u/0"


# -- two jobs on one screen, told apart by nothing but their names ------------
#
# Measured on the deployment 2026-09-21, one pass:
#
#     Send Email:    recognised as a job already stored -- wfl_207e… at 1.00
#     Forward Email: recognised as a job already stored -- wfl_207e… at 1.00
#
# `wfl_207e…` is `Reply to Email`. No threshold could have saved this: the
# shapes really were indistinguishable, they happen on one screen so the
# screen rule cannot help, and `anon` must keep aliasing or one job recorded
# twice splits in two. The name is what was left.


MAILBOX = "https://mail.google.com/mail/u/0"
SEND = [MAILBOX, "button|Send ‪(⌘Enter)‬", "click"]


def test_forwarding_is_not_replying_however_alike_the_clicks_are() -> None:
    reply = _workflow(
        ["g1", "g2"],
        [[MAILBOX, "textbox|Describe your message", "click"], SEND],
        id="wfl_reply",
        title="Reply to Email",
    )
    forward = _workflow(
        ["g3", "g4"],
        [[MAILBOX, "anon|click", "click"], SEND],
        id="wfl_forward",
        title="Forward Email",
    )

    assert resolve(forward, [reply]).kind == "new"


def test_one_job_the_model_phrased_twice_is_still_one_job() -> None:
    """The other direction, and the reason this is a veto rather than a rule
    of its own: a model does not phrase things identically twice, and a name
    that had to match exactly would split every job it renamed."""
    stored = _workflow(["g1", "g2"], SHAPE, id="wfl_a", title="Create a Customer Type")
    again = _workflow(["g3", "g4"], SHAPE, id="wfl_b", title="Create Customer Type")

    assert resolve(again, [stored]).kind == "same_job"


def test_a_job_with_no_name_is_not_kept_apart_by_one() -> None:
    """A name this cannot read is not evidence of difference. The shape still
    decides; this only ever blocks."""
    stored = _workflow(["g1", "g2"], SHAPE, id="wfl_a", title="Create a Customer Type")
    nameless = _workflow(["g3", "g4"], SHAPE, id="wfl_b", title="")

    assert resolve(nameless, [stored]).kind == "same_job"


def test_the_same_evidence_read_twice_is_the_same_evidence_whatever_it_is_called() -> None:
    """The occurrence question is about ids, not about names, and a pass that
    re-read one window must not be made to pay for it twice because a model
    worded the title differently."""
    stored = _workflow(["g1", "g2"], SHAPE, id="wfl_a", title="Reply to Email")
    same = _workflow(["g1", "g2"], SHAPE, id="wfl_b", title="Forward Email")

    assert resolve(same, [stored]).kind == "same_occurrence"


def test_the_words_that_say_nothing_are_not_what_makes_two_names_alike() -> None:
    assert named_alike("Reply to Email", "Forward Email") is False
    assert named_alike("Create a Customer Type", "Create Customer Type") is True
    assert named_alike("Send Email", "Reply to Email") is False


# -- variants fold into one job ------------------------------------------------


def test_a_doing_that_holds_the_stored_job_in_order_contains_it() -> None:
    """Containment is the stored job's steps appearing, in time order, inside
    the doing -- not the doing merely being bigger."""
    stored = _workflow(["ges_a", "ges_b"], SHAPE, id="wfl_stored")
    bigger = _workflow(
        ["ges_c", "ges_d", "ges_e", "ges_f"],
        [SHAPE[0], [WMS, "extra", "click"], SHAPE[1], [WMS, "more", "type"]],
    )

    resolution = resolve(bigger, [stored])

    assert resolution.kind == "same_job"
    assert resolution.contains is True


def test_a_bigger_doing_that_does_the_steps_in_another_order_does_not_contain_it() -> None:
    """Same job by the shape, and bigger -- but the stored steps are not a
    subsequence of it, so growing the job into it would reorder what works."""
    stored = _workflow(["ges_a", "ges_b"], SHAPE, id="wfl_stored")
    reordered = _workflow(
        ["ges_c", "ges_d", "ges_e"],
        [SHAPE[1], SHAPE[0], [WMS, "extra", "click"]],
    )

    resolution = resolve(reordered, [stored])

    assert resolution.kind == "same_job"
    assert resolution.contains is False


def test_a_small_stored_job_wholly_inside_a_bigger_doing_is_that_job() -> None:
    """A later doing that also presses Sign In holds every stored entry, in
    order, and is the same job grown -- not a new one."""
    stored = _workflow(
        ["ges_a", "ges_b"],
        [[KEYCLOAK, "name|Username or email", "type"], [KEYCLOAK, "anon|type", "type"]],
        id="wfl_stored",
        title="Log in to Keycloak",
    )
    doing = _workflow(
        ["ges_c", "ges_d", "ges_e"],
        [
            [KEYCLOAK, "name|Username or email", "type"],
            [KEYCLOAK, "anon|type", "type"],
            [KEYCLOAK, "button|Sign In", "click"],
        ],
        title="Log in to Keycloak",
    )

    resolution = resolve(doing, [stored])

    assert resolution.kind == "same_job"
    assert resolution.workflow_id == "wfl_stored"
    assert resolution.contains is True


def test_an_unnamed_stored_step_matches_a_named_one_in_the_doing() -> None:
    """The alias runs both ways: which recording could name the control is a
    property of the recording, whichever of the two is stored."""
    stored = _workflow(
        ["ges_a", "ges_b"],
        [[MAIL, "anon|click", "click"], [MAIL, "button|Send", "click"]],
        id="wfl_stored",
    )
    again = _workflow(
        ["ges_c", "ges_d"],
        [[MAIL, "link|Reply", "click"], [MAIL, "button|Send", "click"]],
    )

    resolution = resolve(again, [stored])

    assert resolution.kind == "same_job"
    assert resolution.score == 1.0


B2C = "https://idp-chooser.example"


def test_two_sign_ins_to_one_system_are_one_job_whatever_way_they_came() -> None:
    """One went through an identity chooser first, the other straight to the
    password page; both are tagged as signing in, and both sign in to the
    same system. The path to the password box is not the job."""
    direct = _workflow(
        ["ges_a", "ges_b"],
        [[KEYCLOAK, "name|Username or email", "type"], [KEYCLOAK, "anon|type", "type"]],
        id="wfl_direct",
        title="Log in to Keycloak",
        signs_in=True,
    )
    chooser = _workflow(
        ["ges_c", "ges_d", "ges_e"],
        [
            [B2C, "link|Local users", "click"],
            [f"{KEYCLOAK}/login-actions", "textbox|Username", "type"],
            [f"{KEYCLOAK}/login-actions", "button|Sign In", "click"],
        ],
        title="Log in using Azure B2C SSO",
        signs_in=True,
    )
    lands = {"wfl_direct": (KEYCLOAK, WMS), chooser.id: (KEYCLOAK, WMS)}

    resolution = resolve(chooser, [direct], signs_in_to=lands)

    assert resolution.kind == "same_job"
    assert resolution.workflow_id == "wfl_direct"


def test_two_sign_ins_to_two_systems_stay_two_jobs() -> None:
    one = _workflow(["ges_a", "ges_b"], SHAPE, id="wfl_one", title="Log in", signs_in=True)
    other = _workflow(
        ["ges_c", "ges_d"], [[MAIL, "x", "type"], [MAIL, "y", "click"]], signs_in=True
    )

    lands = {"wfl_one": (KEYCLOAK, WMS), other.id: (MAIL, WMS)}

    assert resolve(other, [one], signs_in_to=lands).kind == "new"


def test_a_job_that_does_not_sign_in_is_not_folded_into_one_that_does() -> None:
    signing = _workflow(["ges_a", "ges_b"], SHAPE, id="wfl_one", signs_in=True)
    other = _workflow(["ges_c", "ges_d"], [[MAIL, "x", "type"], [MAIL, "y", "click"]])

    lands = {"wfl_one": (KEYCLOAK, WMS), other.id: (KEYCLOAK, WMS)}

    assert resolve(other, [signing], signs_in_to=lands).kind == "new"


def test_two_applications_behind_one_identity_provider_stay_two_sign_ins() -> None:
    one = _workflow(["ges_a", "ges_b"], SHAPE, id="wfl_one", title="Log in", signs_in=True)
    other = _workflow(["ges_c", "ges_d"], SHAPE, title="Log in", signs_in=True)

    lands = {"wfl_one": (KEYCLOAK, WMS), other.id: (KEYCLOAK, MAIL)}

    assert resolve(other, [one], signs_in_to=lands).kind == "new"


def test_the_sign_in_twin_whose_shape_is_closest_wins() -> None:
    """Two stored copies of one sign-in (the deployment holds them today): a
    new doing goes to the one it most resembles, not to whichever is older."""
    older = _workflow(
        ["ges_a", "ges_b"],
        [[MAIL, "x", "type"], [MAIL, "y", "click"]],
        id="wfl_older",
        signs_in=True,
    )
    closer = _workflow(["ges_c", "ges_d"], SHAPE, id="wfl_closer", signs_in=True)
    doing = _workflow(["ges_e", "ges_f"], SHAPE, signs_in=True)
    key = (KEYCLOAK, WMS)
    lands = {"wfl_older": key, "wfl_closer": key, doing.id: key}

    assert resolve(doing, [older, closer], signs_in_to=lands).workflow_id == "wfl_closer"
