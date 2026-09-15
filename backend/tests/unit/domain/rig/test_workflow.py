from sro.domain.skill.workflow import Step, Workflow, cited_ids, new_workflow_id


def _workflow(**over: object) -> Workflow:
    base: dict[str, object] = {
        "id": new_workflow_id(),
        "tenant": "acme",
        "title": "create a supplier",
        "narrative": "the operator created a supplier and set its status",
        "systems": ["https://wms.example", "https://sap.example"],
        "steps": [
            Step(
                order=0,
                says="create the supplier",
                system="https://wms.example",
                cites=["ges_1", "ges_2"],
                parameters=["supplier_name"],
            ),
            Step(
                order=1,
                says="set the status",
                system="https://sap.example",
                cites=["ges_3"],
                parameters=[],
            ),
        ],
        "parameters": [{"name": "supplier_name", "seen_values": ["TestYonder2"]}],
        "shape_key": [["https://wms.example", "clientCode", "type"]],
        "same_as": None,
        "pass_id": "pas_1",
    }
    return Workflow(**{**base, **over})


def test_a_workflow_id_has_the_rig_shape() -> None:
    assert new_workflow_id().startswith("wfl_") and len(new_workflow_id()) == 36


def test_cited_ids_gathers_every_step() -> None:
    assert cited_ids(_workflow()) == {"ges_1", "ges_2", "ges_3"}


def test_a_title_naming_one_doings_value_loses_it() -> None:
    """The defect this exists for, in the store's own words: a customer type
    observed as DSS, DPP, CCD and CCF, under a title that says DSS. The title
    is what the offer card shows and what a person reads when deciding whether
    a new demonstration is the same job, so one run's value in it makes every
    later doing look like different work."""
    workflow = _workflow(
        title="Create Customer Type DSS",
        parameters=[
            {"name": "customertype-customerType", "seen_values": ["DSS", "DPP", "CCD", "CCF"]},
            {"name": "customertype-longDescription", "seen_values": ["leaning SRO 3"]},
        ],
    )

    workflow.generalise_title()

    assert workflow.title == "Create Customer Type"


def test_the_value_goes_and_the_preposition_it_hung_off_goes_with_it() -> None:
    """A title ending on `for` is not a job's name. "Create a Carrier Cross Reference
    for" reads as truncated rather than as generalised: the word the value hung
    off leaves with it."""
    workflow = _workflow(
        title="Create a Carrier Cross Reference for Test Drive LLC",
        parameters=[{"name": "customerName", "seen_values": ["Test Drive LLC", "Acme Freight"]}],
    )

    workflow.generalise_title()

    assert workflow.title == "Create a Carrier Cross Reference"


def test_a_longer_value_is_taken_out_before_the_shorter_one_inside_it() -> None:
    """The equipment type was done as DDD and then as DDDRO. Taking DDD first
    would leave the title reading "Create Warehouse Equipment Type RO"."""
    workflow = _workflow(
        title="Create Warehouse Equipment Type DDDRO",
        parameters=[{"name": "vehicleTypeId", "seen_values": ["DDD", "DDDRO"]}],
    )

    workflow.generalise_title()

    assert workflow.title == "Create Warehouse Equipment Type"


def test_a_word_that_merely_resembles_a_value_is_not_mangled() -> None:
    """Whole words only. `DSS` inside `DSSR`, and `TEST` inside `TESTING`, are
    the job's own name -- a title is not a place to go hunting substrings."""
    workflow = _workflow(
        title="Review DSSR Mappings and the TESTING Queue",
        parameters=[{"name": "code", "seen_values": ["DSS", "TEST"]}],
    )

    workflow.generalise_title()

    assert workflow.title == "Review DSSR Mappings and the TESTING Queue"


def test_a_value_too_short_to_be_quoted_is_never_hunted() -> None:
    """A voice code of 2 is a parameter value like any other, and "Wave 2" is
    a job's name. Below K_MIN_VALUE_LENGTH a match in the title is a
    coincidence rather than a quotation."""
    workflow = _workflow(
        title="Release Wave 2 to the Floor",
        parameters=[{"name": "voiceCode", "seen_values": ["2", "3"]}],
    )

    workflow.generalise_title()

    assert workflow.title == "Release Wave 2 to the Floor"


def test_a_title_that_is_nothing_but_its_values_keeps_the_name_it_has() -> None:
    """A job with a bad name beats a job with no name: an offer card headed by
    an empty string is worse than one headed by a value."""
    workflow = _workflow(
        title="DSS",
        parameters=[{"name": "customerType", "seen_values": ["DSS", "DPP"]}],
    )

    workflow.generalise_title()

    assert workflow.title == "DSS"


def test_a_parameter_the_model_declared_itself_says_nothing_about_the_title() -> None:
    """`seen_values` is written by the pass that diffs two doings. A parameter
    that arrived on a model answer has no values observed, and reading one off
    a free-form dict is how a title loses a word to a key nobody promised."""
    workflow = _workflow(
        title="Create Customer Type DSS",
        parameters=[{"name": "customerType", "description": "DSS"}],
    )

    workflow.generalise_title()

    assert workflow.title == "Create Customer Type DSS"
