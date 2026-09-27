from sro.domain.chat.asking import Pending, answered
from sro.domain.chat.request import K_A_LOGIN, Candidate, field_of, read_of
from sro.domain.execution.field_classes import FieldClass, FieldLimits
from sro.domain.skill.signing_in import Logins

THREAD = "Hi, please set up a new client category GT7 for Finance. Thanks"

JOB = Candidate(
    id="wfl_ct",
    title="Create a Customer Type",
    fields=(
        FieldClass(
            "Customer Type", "required", ("Customer Type", "Type"), FieldLimits(max_length=3)
        ),
        FieldClass(
            "Department", "never", ("Department",), FieldLimits(options=("Finance", "Operations"))
        ),
    ),
    aliases={"client category": "Customer Type"},
    seen={"Customer Type": ("GT0", "GT1")},
)


def _value(field: str, value: str, quote: str) -> dict[str, str]:
    return {"field": field, "value": value, "quote": quote}


def test_an_alias_outranks_every_other_reading_of_the_wording() -> None:
    assert field_of("Client Category", JOB) == ("Customer Type", True)
    assert field_of("type", JOB) == ("Customer Type", True)
    assert field_of("Department", JOB) == ("Department", False)
    assert field_of("colour", JOB) is None


def test_a_quoted_value_binds_to_its_field() -> None:
    read = read_of(
        {
            "job": "wfl_ct",
            "sure": True,
            "values": [_value("client category", "GT7", "client category GT7")],
        },
        [JOB],
        THREAD,
    )
    assert (read.job, read.sure, read.values, read.missing) == (
        "wfl_ct",
        True,
        {"Customer Type": "GT7"},
        [],
    )


def test_a_quote_that_is_not_in_the_thread_makes_the_reading_unsure_and_drops_the_value() -> None:
    read = read_of(
        {"job": "wfl_ct", "sure": True, "values": [_value("Customer Type", "GT9", "category GT9")]},
        [JOB],
        THREAD,
    )
    assert (read.sure, read.values, read.missing) == (False, {}, ["Customer Type"])


def test_a_value_that_is_not_in_its_quote_is_not_taken() -> None:
    read = read_of(
        {"job": "wfl_ct", "sure": True, "values": [_value("Customer Type", "GT8", "category GT7")]},
        [JOB],
        THREAD,
    )
    assert read.sure is False and "Customer Type" not in read.values


def test_a_value_that_cannot_fit_is_dropped_and_asked_for() -> None:
    thread = "please set up client category GT700"
    read = read_of(
        {
            "job": "wfl_ct",
            "sure": True,
            "values": [_value("Customer Type", "GT700", "category GT700")],
        },
        [JOB],
        thread,
    )
    assert read.values == {} and read.missing == ["Customer Type"]
    assert read.refused == {"Customer Type": "longer than 3 characters"}


def test_a_value_on_a_field_the_job_never_filled_goes_aside_under_its_label() -> None:
    read = read_of(
        {
            "job": "wfl_ct",
            "sure": True,
            "values": [
                _value("Customer Type", "GT7", "category GT7"),
                _value("Department", "Finance", "for Finance"),
            ],
        },
        [JOB],
        THREAD,
    )
    assert read.aside == {"Department": "Finance"}


def test_a_value_the_reader_could_not_place_goes_aside_under_the_mails_wording() -> None:
    read = read_of(
        {
            "job": "wfl_ct",
            "sure": True,
            "values": [
                _value("Customer Type", "GT7", "category GT7"),
                _value("cost centre", "Finance", "for Finance"),
            ],
        },
        [JOB],
        THREAD,
    )
    assert read.aside == {"cost centre": "Finance"}


def test_a_job_that_was_not_a_candidate_is_no_job() -> None:
    assert read_of({"job": "wfl_other", "sure": True, "values": []}, [JOB], THREAD).job is None


# --- what the real greyorange chat showed (2026-09-26, redacted to shape) ----

CUSTOMER_TYPE = Candidate(
    id="wfl_ct",
    title="Create a Customer Type",
    fields=(
        FieldClass("Customer Type", "required", ("Customer Type",), FieldLimits(max_length=4)),
        FieldClass(
            "Customer Type Description",
            "required",
            ("Customer Type Description", "Description"),
            FieldLimits(max_length=40),
        ),
        FieldClass("Department", "sometimes", ("Department",), FieldLimits(max_length=10)),
        FieldClass("Manufacturer", "sometimes", ("Manufacturer",), FieldLimits(max_length=10)),
    ),
    aliases={},
    seen={},
)

REPLY = Candidate(
    id="wfl_reply",
    title="Reply to Email",
    fields=(FieldClass("Reply", "required", ("Reply",), FieldLimits()),),
    aliases={},
    seen={},
)


def test_a_stated_request_binds_both_values_and_asks_no_which_job() -> None:
    """ "customer type :- RRF and description :- ..." got "Did you mean Create a
    Customer Type or Reply to Email or Reply to Email?". Both values were
    stated; only one of the two jobs they fill."""
    thread = "customer type :- RRF and description :- is the work of cutomer is RRF"
    read = read_of(
        {
            "job": "wfl_ct",
            "sure": False,
            "also": ["wfl_reply"],
            "values": [
                _value("customer type", "RRF", "customer type :- RRF"),
                _value(
                    "description",
                    "is the work of cutomer is RRF",
                    "description :- is the work of cutomer is RRF",
                ),
            ],
        },
        [CUSTOMER_TYPE, REPLY],
        thread,
    )
    assert read.values == {
        "Customer Type": "RRF",
        "Customer Type Description": "is the work of cutomer is RRF",
    }
    assert (read.also, read.sure, read.missing) == ([], True, [])


def test_an_optional_field_is_never_missing() -> None:
    """thr_c563 asked for Department, then Manufacturer: neither is required."""
    read = read_of(
        {"job": "wfl_ct", "sure": True, "values": [_value("Customer Type", "RRF", "type RRF")]},
        [CUSTOMER_TYPE],
        "new customer type RRF",
    )
    assert read.missing == ["Customer Type Description"]


def test_a_value_whose_quote_names_another_field_is_never_taken_for_this_one() -> None:
    thread = "customer type :- RRF and description :- first run"
    read = read_of(
        {
            "job": "wfl_ct",
            "sure": True,
            "values": [_value("description", "RRF", "customer type :- RRF")],
        },
        [CUSTOMER_TYPE],
        thread,
    )
    assert "Customer Type Description" not in read.values
    assert read.refused == {"Customer Type Description": "its quote names Customer Type"}
    assert "Customer Type Description" in read.missing


def test_a_sign_in_name_is_never_a_job_value() -> None:
    """thr_163b: the operator sent "RKUCHIYAGM", the sign-in username, and it was
    stored as Create a Client's Address."""
    client = Candidate(
        id="wfl_client",
        title="Create a Client",
        fields=(FieldClass("Address", "required", ("Address",), FieldLimits()),),
        aliases={},
        seen={},
        logins=Logins(names=frozenset({"rkuchiyagm"})),
    )
    read = read_of(
        {
            "job": "wfl_client",
            "sure": True,
            "values": [_value("Address", "RKUCHIYAGM", "RKUCHIYAGM")],
        },
        [client],
        "RKUCHIYAGM",
    )
    assert read.values == {} and read.missing == ["Address"]
    assert read.refused == {"Address": "a sign-in name, never a job's value"}
    aside = read_of(
        {
            "job": "wfl_client",
            "sure": True,
            "values": [_value("username", "RKUCHIYAGM", "RKUCHIYAGM")],
        },
        [client],
        "username RKUCHIYAGM",
    )
    assert aside.aside == {}, "nor is it carried aside into the run"


def test_one_thing_with_a_bad_value_keeps_the_others() -> None:
    thread = "three types: GT1, GT2 and GT3"
    read = read_of(
        {
            "job": "wfl_ct",
            "sure": True,
            "values": [],
            "items": [
                {"values": [_value("Customer Type", "GT1", "GT1")]},
                {"values": [_value("Customer Type", "GT9", "GT9")]},
                {"values": [_value("Customer Type", "GT3", "GT3")]},
            ],
        },
        [JOB],
        thread,
    )
    assert read.items == [{"Customer Type": "GT1"}, {"Customer Type": "GT3"}]
    assert read.sure is False


# --- review round 1 ----------------------------------------------------------


def test_a_value_is_in_its_quote_only_whole_and_in_the_same_case() -> None:
    """A truncation ("RR" of "RRF") or a recased value ("rrf") is never taken."""
    thread = "customer type :- RRF"
    for value in ("RR", "rrf"):
        read = read_of(
            {
                "job": "wfl_ct",
                "sure": True,
                "values": [_value("customer type", value, "customer type :- RRF")],
            },
            [CUSTOMER_TYPE],
            thread,
        )
        assert read.values == {} and read.sure is False, value


ZERO = Candidate(id="wfl_nav", title="Navigate to Receiving", fields=(), aliases={}, seen={})


def test_a_job_with_no_fields_never_competes_with_the_job_the_stated_values_settle() -> None:
    thread = "customer type :- RRF and description :- is the work of cutomer is RRF"
    read = read_of(
        {
            "job": "wfl_ct",
            "sure": False,
            "also": ["wfl_nav"],
            "values": [
                _value("customer type", "RRF", "customer type :- RRF"),
                _value(
                    "description",
                    "is the work of cutomer is RRF",
                    "description :- is the work of cutomer is RRF",
                ),
            ],
        },
        [CUSTOMER_TYPE, ZERO],
        thread,
    )
    assert (read.also, read.sure, read.missing) == ([], True, [])


def test_no_stated_value_settles_nothing() -> None:
    read = read_of(
        {"job": "wfl_nav", "sure": False, "also": ["wfl_ct"], "values": []},
        [ZERO, CUSTOMER_TYPE],
        "go to receiving",
    )
    assert (read.also, read.sure) == (["wfl_ct"], False)


def test_a_refused_optional_value_is_dropped_never_asked_for() -> None:
    """thr_c563: Manufacturer "whatever we have" was refused, then asked for."""
    thread = "customer type RRF, description first run, manufacturer whatever we have"
    read = read_of(
        {
            "job": "wfl_ct",
            "sure": True,
            "values": [
                _value("customer type", "RRF", "customer type RRF"),
                _value("description", "first run", "description first run"),
                _value("manufacturer", "whatever we have", "manufacturer whatever we have"),
            ],
        },
        [CUSTOMER_TYPE],
        thread,
    )
    assert read.refused == {"Manufacturer": "longer than 10 characters"}
    assert read.missing == [] and "Manufacturer" not in read.values


def test_a_value_that_names_a_field_itself_is_still_that_value() -> None:
    thread = "description: returns customer type"
    read = read_of(
        {
            "job": "wfl_ct",
            "sure": True,
            "values": [
                _value("description", "returns customer type", "returns customer type"),
            ],
        },
        [CUSTOMER_TYPE],
        thread,
    )
    assert read.values == {"Customer Type Description": "returns customer type"}
    assert read.refused == {}


WMS = "wms.example"
SIGNED = Logins(names=frozenset({"rkuchiyagm"}), labels=frozenset({(WMS, "username")}))


def test_a_username_the_thread_states_is_never_a_job_value_nor_carried_aside() -> None:
    client = Candidate(
        id="wfl_client",
        title="Create a Client",
        fields=(FieldClass("Address", "required", ("Address",), FieldLimits()),),
        aliases={},
        seen={},
        logins=SIGNED,
        systems=frozenset({WMS}),
    )
    thread = "username QATEST01, please add the client"
    read = read_of(
        {
            "job": "wfl_client",
            "sure": True,
            "values": [
                _value("Address", "QATEST01", "username QATEST01"),
                _value("username", "QATEST01", "username QATEST01"),
            ],
        },
        [client],
        thread,
    )
    assert read.values == {} and read.aside == {}
    assert read.refused == {"Address": K_A_LOGIN}


def test_a_job_s_own_username_field_is_filled_like_any_other() -> None:
    """A WMS Create-a-User job: its Username is the new user's, not a login."""
    user = Candidate(
        id="wfl_user",
        title="Create a User",
        fields=(FieldClass("Username", "required", ("Username",), FieldLimits()),),
        aliases={},
        seen={},
        logins=SIGNED,
        systems=frozenset({WMS}),
    )
    read = read_of(
        {"job": "wfl_user", "sure": True, "values": [_value("username", "JDOE", "username JDOE")]},
        [user],
        "new user, username JDOE",
    )
    assert read.values == {"Username": "JDOE"} and read.sure is True


def test_a_chat_answer_that_is_a_sign_in_name_is_not_taken() -> None:
    """thr_163b in chat: a bare "RKUCHIYAGM" under a pending Address question."""
    pending = Pending("wfl_client", "Create a Client", {}, ("Address",))
    assert answered(pending, "RKUCHIYAGM", SIGNED) == pending
    assert answered(pending, "12 Main St", SIGNED).values == {"Address": "12 Main St"}


def _client(logins: Logins, *on: str) -> Candidate:
    return Candidate(
        id="wfl_client",
        title="Create a Client",
        fields=(FieldClass("Address", "required", ("Address",), FieldLimits()),),
        aliases={},
        seen={},
        logins=logins,
        systems=frozenset(on),
    )


BOX_USER = Logins(labels=frozenset({(WMS, "user")}))


def _address(client: Candidate, value: str, thread: str) -> tuple[dict[str, str], dict[str, str]]:
    got = read_of(
        {"job": "wfl_client", "sure": True, "values": [_value("Address", value, thread)]},
        [client],
        thread,
    )
    return got.values, got.refused


def test_a_generic_sign_in_box_name_near_a_value_does_not_make_it_a_login() -> None:
    thread = "user asked for address 12 Main St"
    assert _address(_client(BOX_USER, WMS), "12 Main St", thread) == ({"Address": "12 Main St"}, {})


def test_a_value_stated_after_the_sign_in_box_name_is_a_login() -> None:
    thread = "user: RKUCHIYAGM"
    assert _address(_client(BOX_USER, WMS), "RKUCHIYAGM", thread) == ({}, {"Address": K_A_LOGIN})


def test_one_system_s_sign_in_box_name_says_nothing_about_another_system_s_jobs() -> None:
    thread = "user: RKUCHIYAGM"
    got = _address(_client(BOX_USER, "other.example"), "RKUCHIYAGM", thread)
    assert got == ({"Address": "RKUCHIYAGM"}, {})


COST = Candidate(
    id="wfl_cc",
    title="Book a cost",
    fields=(FieldClass("department", "sometimes", ("department", "Department"), FieldLimits(5)),),
    aliases={"cost centre": "Department"},
    seen={},
)


def test_an_alias_lands_on_the_parameter_its_label_names_and_its_limits_apply() -> None:
    def said(wording: str) -> dict[str, str]:
        thread = f"Please book it to {wording} Finance Team"
        read = read_of(
            {
                "job": "wfl_cc",
                "values": [_value(wording, "Finance Team", f"{wording} Finance Team")],
            },
            [COST],
            thread,
        )
        return {**read.refused, **{f"value:{k}": v for k, v in read.values.items()}}

    assert field_of("cost centre", COST) == ("department", True)
    assert said("cost centre") == said("Department") == {"department": "longer than 5 characters"}
