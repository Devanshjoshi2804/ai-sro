# Notes for `backend/evals/suites/reader.py`

The request-reader suite: given a real request mail, does READ_REQUEST pick the job, know it is sure, and read each value into its field?

## `_job`, [line 23](../../../../../backend/evals/suites/reader.py#L23): Note on the line above

Code: `raw.pop("same_as", None)`

> Cases captured before M1 carry `same_as`, which `Workflow` no longer has.
> The key is dropped on load so those cases still score; it was never read.

## `Reader.cases`, [line 34](../../../../../backend/evals/suites/reader.py#L34): Design

> One case per mail behind a job (`mails_behind`). That mail is removed from
> every job's `asked_by` examples, so the reader never sees the answer among
> its examples. Expected: every job with the same normalised title (two
> copies of one job are both right), and each seen value the mail quotes,
> under its field.

## `Reader.run`, [line 65](../../../../../backend/evals/suites/reader.py#L65): Design

> Runs the production `understand`. Passes only when the job is right, the
> reader is sure, and every expected value is read into its field.
> An errored call is carried on `Scored.error`. `Reader.asker` is the
> container's plain asker, the one the mail door gives `understand`.
