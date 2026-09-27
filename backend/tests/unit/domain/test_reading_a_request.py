from sro.domain.chat.request import Candidate, field_of, read_of
from sro.domain.execution.field_classes import FieldClass, FieldLimits

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
        logins=frozenset({"rkuchiyagm"}),
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
