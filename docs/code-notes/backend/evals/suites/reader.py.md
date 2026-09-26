# Notes for `backend/evals/suites/reader.py`

The request-reader suite: given a real request mail, does READ_REQUEST pick the job, know it is sure, and read each value into its field?

## `Reader.cases`, [line 33](../../../../../backend/evals/suites/reader.py#L33): Design

> One case per mail behind a job (`mails_behind`). That mail is removed from
> every job's `asked_by` examples, so the reader never sees the answer among
> its examples. Expected: every job with the same normalised title (two
> copies of one job are both right), and each seen value the mail quotes,
> under its field.

## `Reader.run`, [line 64](../../../../../backend/evals/suites/reader.py#L64): Design

> Runs the production `understand`. Passes only when the job is right, the
> reader is sure, and every expected value is read into its field.
> An errored call is carried on `Scored.error`. `Reader.asker` is the
> container's plain asker, the one the mail door gives `understand`.
