// The runs a mail started, out of the list the panel polls.
//
// QA 2026-09-29: the backend read a mail, started its run on Steel, and it
// held in 12 s -- while Home said "0 offers". Nothing here starts anything:
// the backend started these, and this only says which of them are the mail's
// and what they end.
//
// Pure, so the test is arithmetic rather than a browser.

/** How many of this operator's newest runs are looked through for today's
 * mail runs. ponytail: a day with more runs than this hides the older mail
 * runs; ask the list for mail runs only if that ever happens. */
export const K_MAIL_RUNS = 50;

/** Today's mail runs (the local day), newest first as the list gave them, not
 * dismissed, each titled -- and, where the run knows only its thread (a press
 * on a card started it), given the subject the card was showing. */
export function mailRunsOfToday(
  runs,
  { now, dismissed = [], titles = new Map(), nudges = [] },
) {
  const today = new Date(now).toDateString();
  const gone = new Set(dismissed);
  return runs
    .filter(
      (run) =>
        run.mail &&
        !gone.has(run.id) &&
        new Date(run.started_at).toDateString() === today,
    )
    .map((run) => {
      const offered = nudges.find((one) => one.offer && one.offer === run.offer);
      return {
        ...run,
        title: titles.get(run.workflow_id) || offered?.title || run.workflow_id,
        mail: {
          ...run.mail,
          subject: run.mail.subject || offered?.mailSubject || "",
        },
      };
    });
}

/** Every open card offering what a run has already taken, ended and naming
 * that run: one mail, one offer, one run -- a card beside the run it offers
 * is a "Yes, do it" for work already under way (the user, 2026-09-29). The
 * backend refuses the second start anyway (`OfferTaken`); this is the half
 * that stops the panel asking. */
export function endTheOffersThatRan(nudges, runs, now) {
  const ran = new Map(
    runs.filter((run) => run.offer).map((run) => [run.offer, run.id]),
  );
  return nudges.map((one) =>
    one.state === "open" && one.offer && ran.has(one.offer)
      ? { ...one, state: "accepted", endedAt: now, runId: ran.get(one.offer) }
      : one,
  );
}
