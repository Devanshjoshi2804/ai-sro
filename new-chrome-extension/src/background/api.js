// Every call to the backend. See docs/14-extension-protocol.md.

import { state } from "./state.js";

export class ApiError extends Error {
  // `where` is the call that failed, as "METHOD /path". A backend that answers
  // 500 with no body used to surface in the panel as the bare words "HTTP 500",
  // which says nothing an operator or a log reader can act on -- not which of
  // the dozen calls this extension makes had failed, so not whether the
  // recording, the run, or the registration was the thing that broke.
  constructor(status, problem, where = "") {
    super(
      problem?.detail ||
        problem?.title ||
        `HTTP ${status}${where ? ` from ${where}` : ""}`,
    );
    this.status = status;
    this.problem = problem;
    this.where = where;
  }
}

async function call(
  path,
  { method = "GET", body, form, signal, asDevice = true } = {},
) {
  const [base, token, secret] = await Promise.all([
    state.apiUrl(),
    state.token(),
    state.deviceSecret(),
  ]);
  // A multipart body names its own content type, boundary and all, and a
  // Content-Type set here would replace it with one the boundary is missing
  // from -- which every parser reads as a body with no parts in it.
  const response = await fetch(`${base}${path}`, {
    method,
    signal,
    headers: {
      Authorization: `Bearer ${token}`,
      // Two things, because they answer two questions. The credential says
      // which tenant is asking; it cannot say which browser, and every
      // device-scoped path is `/v1/agents/{device_id}/...` -- one of which
      // fires a run in a live warehouse. Sent on every call rather than on the
      // four that check it: it goes to the same backend either way, and a list
      // of which endpoints are allowed to see it is a list that goes stale.
      // `asDevice: false` for the one route that is the TENANT's and refuses a
      // browser proving itself (`tenant_only` 403s rather than quietly serving
      // the request as the tenant). This extension is already holding the
      // tenant's own credential -- the operator pasted it -- so the header is
      // left off rather than the guard being loosened for every device.
      ...(secret && asDevice ? { "X-Device-Secret": secret } : {}),
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    },
    body:
      form !== undefined
        ? form
        : body === undefined
          ? undefined
          : JSON.stringify(body),
  });

  if (response.status === 401) {
    // The same rule the console follows: a credential that is not accepted is
    // dropped, so the operator lands back on the paste screen instead of every
    // later call failing quietly.
    await state.setToken("");
    throw new ApiError(401, { detail: "that credential was not accepted" });
  }
  if (!response.ok) {
    throw new ApiError(
      response.status,
      await response.json().catch(() => null),
      `${method} ${path}`,
    );
  }
  return response.status === 204 ? null : response.json();
}

/** One workflow run, in the shape the panel's run card draws.
 *
 * Its own function so a run read from the LIST is the same shape as one
 * read on its own. The backend answers whole rows -- `list_workflow_runs`
 * says so: "the rows are whole, where the rig sent one line each with the
 * full record a GET away" -- and the panel could not draw them, because only
 * `rigRun` mapped `outcome`/`order`/`verdict` onto `status`/`index`/`outcome`.
 * So the history overlay held twelve runs in full and could show a title and
 * a word.
 *
 * The mapping is a whitelist, and the comment inside it records what happens
 * when somebody forgets to add to it: a card that silently draws nothing and
 * looks like code nobody changed. One copy is one place to add.
 */
export function asPanelRun(run) {
  return {
    id: run.id,
    source: "rig",
    status: run.outcome,
    // Which of the two ways it did the job, and what it could not find.
    //
    // This mapping is a whitelist -- what is not named here does not reach
    // the panel -- and these two were added to the row and to the card
    // without ever being added in between. So every run drew "Nobody was
    // watching, so it replayed the call" including the ones somebody
    // pressed and watched, and a run that stopped to ask carried no names
    // for the panel to notice. Measured on the deployment, 2026-09-17 at
    // 10:49: `watched=true` on the row, "nobody was watching" on the card.
    watched: Boolean(run.watched),
    needs: run.needs || [],
    // The question a running run is parked on: a run waiting on a person is
    // not "Running…" (QA 2026-09-30, PJ26).
    asking: run.asking || "",
    // What the run wrote, so the card can name the record rather than only
    // reporting the machinery that made it. Added here THIRD, after the row
    // and the card, which is precisely the mistake the paragraph above
    // records -- a whitelist nobody adds to is a card that silently draws
    // nothing and looks like code that was never changed.
    values: run.values || {},
    // And what takes it back. Added here, in `finishing.js`, and drawn on
    // the card -- all three, because this is the whitelist whose own comment
    // above records what happens when one of them is forgotten: a card that
    // silently draws nothing and looks like code nobody changed.
    undo: run.undo || null,
    undoes_by: run.undoes_by || null,
    // And, the other way round, which run THIS one takes back -- so an undo
    // that failed reads as the record still being out there rather than as
    // a job that failed on its own.
    undoes_run: run.undoes_run || null,
    // Whether a person may simply press it again: the run stopped and
    // nothing it did may have landed. The backend decides it -- a second
    // press after a write nobody could confirm is two records.
    try_again: Boolean(run.try_again),
    // And which job to press: `values` and `items` were already here, and
    // this is the third thing a press needs. The run's own conversation is
    // deliberately not carried -- a retry that comes up short asks in the
    // panel, where the person who pressed it is.
    workflow_id: run.workflow_id || "",
    // Where Steel shows this run's own tab, view-only, while it has one.
    live_view_url: run.live_view_url || "",
    // WHEN it ran. The fourth thing this whitelist was missing, found the way
    // the paragraph above says they are found: `Recent tasks` drew twelve
    // lines reading `Log in to Keycloak` and nothing else -- no outcome, no
    // time -- because the list reads `started_at` and `status` off a row that
    // carried neither. Measured on the deployment 2026-09-21. The backend has
    // both on every row and always has.
    started_at: run.started_at || "",
    finished_at: run.finished_at || null,
    // What it read out of the mail, so the card can say where a value it
    // was never given came from.
    gathered: run.gathered || {},
    doing: run.doing || "",
    // The things this run was asked to do its repeated block for. The card
    // draws a line per thing so somebody watching knows which of the three
    // records is being made now, and how many are left.
    items: run.items || [],
    // The offer this run is the one run of, and the mail it came from --
    // subject, sender, when it arrived, where to open it; never its body.
    // Home draws a card per mail run from these, and ends any card still
    // offering what a run already took.
    offer: run.offer || "",
    mail: run.mail || null,
    steps: (run.steps || []).map((step) => ({
      index: step.order,
      // Which thing on the list this row was done for, and which step of the
      // job it is. `null` on every step of a job that does one thing once,
      // which is most of them.
      item: step.item ?? null,
      of_step: step.of_step ?? step.order,
      // What the warehouse called the record this step made, where it made
      // one. The panel says which records a run created, because nothing
      // here can take one back and a person has to be able to go and look.
      made: step.made || {},
      outcome: step.verdict,
      says: step.says,
      reason: step.reason,
      // What the step would send, on a step the rig has stopped to ask
      // about. Nothing has gone out yet -- this is the command itself, and
      // it is the only thing the panel can put in front of the person whose
      // approval the run is waiting for. `null` where there is none, so the
      // card has one shape whichever verdict the step carries.
      sent: step.sent || null,
      // How the control was found -- the locator rung that caught it, or
      // `sight` when no recorded identity did and the model pointed at the
      // screen -- and what the call that planned it cost. Both are the
      // rig's own accounting and neither is invented here: `unpriced` is a
      // call whose cost could not be established -- not a free one -- and
      // the row says so rather than drawing a zero. `stale` is the rig
      // saying the page has moved under this step: found, but not where
      // the job was taught it would be.
      matched_by: step.matched_by || null,
      stale: Boolean(step.stale),
      cost_usd: typeof step.cost_usd === "number" ? step.cost_usd : null,
      unpriced: Boolean(step.unpriced),
    })),
    withheld: run.withheld || [],
  };
}

export const api = {
  register: (label, extensionVersion) =>
    call("/v1/agents/register", {
      method: "POST",
      body: { label, extension_version: extensionVersion },
    }),

  heartbeat: (deviceId, beat) =>
    call(`/v1/agents/${encodeURIComponent(deviceId)}/heartbeat`, {
      method: "POST",
      body: beat,
    }),

  /** Watch this host too, beyond what the tenant excludes by default. */
  grantHost: (deviceId, host) =>
    call(`/v1/agents/${encodeURIComponent(deviceId)}/grants`, {
      method: "POST",
      body: { host },
    }),

  revokeHost: (deviceId, host) =>
    call(
      `/v1/agents/${encodeURIComponent(deviceId)}/grants/${encodeURIComponent(host)}`,
      { method: "DELETE" },
    ),

  observations: (batch) =>
    call("/v1/observations", { method: "POST", body: batch }),

  /** A screenshot or an oversized body, uploaded beside the batch it
   * illustrates. `form` carries device_id, batch_id, kind, file and the
   * frame_index that says which gesture it followed. */
  artifact: (form) =>
    call("/v1/observations/artifacts", { method: "POST", form }),

  policy: () => call("/v1/agents/policy"),

  /** Read this operator's recent mail for the jobs it asks for.
   *
   * POST on a path that reads, because it is not a read: it calls their
   * connector and writes offers into their thread. What comes back is what
   * this look found; the offers themselves arrive in the panel the way every
   * other message does, on the thread poll. */
  fromTheMail: () => call("/v1/chat/from-the-mail", { method: "POST" }),

  /** What this browser is watching its operator's mail for. Asked for here
   * because a watch is evaluated in the browser that has the mailbox open and
   * nowhere else -- no mail is ever sent to the backend, so the rule comes
   * the other way. */
  watches: (deviceId) =>
    call(`/v1/agents/${encodeURIComponent(deviceId)}/watches`),

  /** A mail was recognised. The body is the values the operator marked and
   * nothing else -- not the subject, not the sender, not why. What comes back
   * is the offer; nothing has started. */
  watchMatched: (deviceId, triggerId, values, offerId) =>
    call(
      `/v1/agents/${encodeURIComponent(deviceId)}/watches/${encodeURIComponent(triggerId)}/matched` +
        (offerId ? `?offer=${encodeURIComponent(offerId)}` : ""),
      { method: "POST", body: values },
    ),

  /** The press. The operator saw the offer and said do it, so the values go up
   * again -- nothing was kept at the match, and this browser is where they
   * live. What comes back is the run, or why none started. */
  watchFire: (deviceId, triggerId, values) =>
    call(
      `/v1/agents/${encodeURIComponent(deviceId)}/watches/${encodeURIComponent(triggerId)}/fire`,
      { method: "POST", body: values },
    ),

  /** One skill run, for the panel to say what is happening.
   *
   * The worker knows a run's id; what it is called, which rung it is on and
   * how far through it is are the run's own record. */
  run: (runId) => call(`/v1/runs/${encodeURIComponent(runId)}`),

  /** A workflow run the operator is watching, in the panel's vocabulary.
   *
   * `/v1/workflow-runs/{id}`, not `/v1/runs/{id}`: on this host `/v1/runs`
   * already means a *skill* run, `sro.domain.execution.run.Run`, keyed on a
   * `RunId` and not on a workflow run's plain string. Two aggregates, two id
   * spaces; `workflow_runs.py`'s module docstring is where that was decided.
   *
   * **The mapping layer stays, and this is the reason.** `WorkflowRunModel`'s
   * docstring says phase 5 deletes it "against this" -- the backend answering
   * its own field names. It cannot, because `{index, outcome, status}` are not
   * rig-shaped aliases: they are the *skill* run's own names. `RunModel.status`
   * and `StepOutcomeModel.index` are what `api.run` answers, and `run-card.js`
   * draws both kinds of run from one shape -- `run.status`, `step.index` --
   * telling them apart only by `source`. Deleting this would mean teaching the
   * card a second vocabulary, and the card is one of the files phase 5 states
   * outright it does not change. So the translation happens here, in the one
   * place that already exists for it, and the card keeps one shape to draw.
   *
   * `source: "rig"` is likewise kept: it is what `finishing.js` and the panel
   * read to decide which door to ask about a run, and it is a workflow run
   * either way. Phase 7 is where that word can change, with its readers.
   */
  rigRun: async (runId) =>
    asPanelRun(await call(`/v1/workflow-runs/${encodeURIComponent(runId)}`)),

  /** Stop a workflow run the operator is watching. It takes effect at the next
   * step: a gesture already sent cannot be recalled from a warehouse.
   *
   * **No `device_id`, and no body at all.** The rig's abort took one naming the
   * browser; the row already says which browser is driving it, and a second
   * answer to that question is one that can disagree with the first. The route
   * reads none, so sending one would be a value nothing checks -- and a bare
   * POST is what a tap is. `deviceId` is gone from the signature rather than
   * left unused, so nothing reads a browser id for a call that cannot carry
   * one. */
  rigAbort: (runId) =>
    call(`/v1/workflow-runs/${encodeURIComponent(runId)}/abort`, {
      method: "POST",
    }),

  /** Every job this tenant has proved, with the shape each one has. Read on a
   * five-minute cache by the worker: a shape changes when a job is mined, not
   * when somebody types.
   *
   * `?device_id=` is not decoration and it is not optional: a job's rest is per
   * browser -- three refusals quiet it for the browser that refused and for
   * nobody else -- so a browser served another browser's list spends or earns a
   * colleague's rest, and nothing anywhere goes red. It rides the query beside
   * `X-Device-Secret` in the headers because `asking_device` wants both
   * together; half a pair is a 404, which here means `[]`, which here means an
   * extension that has silently stopped recognising anything.
   *
   * `call` for the headers and a `try` around it for the rule: `[]` on every
   * failure and never a throw. This is read on the gesture path, where a
   * backend that is down must cost the operator nothing at all -- the one
   * reason it is not a bare `call`. */
  shapes: async (deviceId) => {
    try {
      const query = deviceId
        ? `?device_id=${encodeURIComponent(deviceId)}`
        : "";
      const answered = await call(`/v1/shapes${query}`);
      // `can_find` rides along: whether a run can go and find a value nobody
      // typed is a fact about the deployment, and a browser building an offer
      // out of these shapes cannot know it any other way.
      // `takes_over` likewise: whether a press here is run on the server,
      // which reads what the operator already did from their uploads.
      return {
        shapes: answered.shapes || [],
        canFind: Boolean(answered.can_find),
        takesOver: Boolean(answered.takes_over),
      };
    } catch {
      return { shapes: [], canFind: false, takesOver: false };
    }
  },

  /** How an offer ended -- taken, dismissed, done by hand, walked away from.
   *
   * The one measurement that says whether recognising a job early was worth
   * doing, which is why every fate is reported and not just the ones that
   * became runs. */
  reportOffer: async ({ device_id: deviceId, ...rest }) => {
    // Every read inside the guard, the settings read included: this is called
    // with `void` from paths that must not fail, and a rejected storage read
    // outside the `try` is an unhandled rejection rather than a lost record.
    //
    // Returns whether the fate actually landed. It still never throws -- the
    // `void` callers are unchanged -- but the answer is no longer thrown away.
    // This had no status check at all: `await fetch(...)`, result discarded, so
    // a 4xx and a success were the same nothing. That matters more than it
    // looks, because the docstring above is right that this is the one
    // measurement saying whether recognising a job early was worth doing, and
    // the old `catch` comment calling the record "a nicety" contradicted it
    // three lines down.
    //
    // The 403 an earlier note here warned was coming is closed rather than
    // arrived: `call` is the one place `X-Device-Secret` is built, and
    // `?device_id=` goes beside it. Half a pair is `asking_device`'s 404, so
    // neither half is optional.
    //
    // **The browser rides the query, not the body.** The rig read a `device_id`
    // out of the body; `/v1/offers` refuses a request naming no browser with a
    // 403 and writes nothing, because an offer is evidence *about* the browser
    // that showed it -- one a body merely named could spend a colleague's
    // rest, or earn it. Lifted out of the caller's record here rather than at
    // the call site: `service-worker.js`'s `report` writes one record of what
    // happened, and which part of the wire each field rides on is this file's
    // business.
    try {
      await call(
        `/v1/offers${deviceId ? `?device_id=${encodeURIComponent(deviceId)}` : ""}`,
        {
          method: "POST",
          body: rest,
        },
      );
      return true;
    } catch {
      // The offer already happened; losing the record must not break the path
      // that reported it. Said as `false` rather than swallowed, so a caller
      // that wants to count what was lost can.
      return false;
    }
  },

  /** They said yes. The backend starts the job from the step they have reached,
   * and answers with the row it claimed -- `id`, not the rig's `{run_id}`.
   *
   * `/v1/workflow-runs`, not `/v1/runs`, which on this host starts a *skill*
   * run from a preview and would refuse a workflow id outright.
   *
   * The run is the backend's: it picks the executor by tenant (Steel), and
   * `device_id` in the body only records which browser pressed -- this one
   * never drives a step. `offer` names the offer the press answers; the
   * backend starts one run per offer and answers a second start with it.
   *
   * No `started_by`: the backend reads who authorised it off the credential,
   * and a request that says who authorised it is a signature nobody checked. */
  rigStart: (body) => call("/v1/workflow-runs", { method: "POST", body }),

  /** Ask, in the operator's own conversation, for what an offer still needs.
   *
   * Nothing runs. What comes back is the question that was asked, or `""` for
   * an offer that turned out to need nothing -- which the caller should then
   * simply start. */
  askAboutOffer: (body) =>
    call("/v1/chat/about-an-offer", { method: "POST", body }),

  /** Send the drafted mail the operator has just read.
   *
   * Two ids and no words. What goes out is re-read from the thread the draft
   * was shown in, so what is sent and what was read cannot be two different
   * things -- a body sent from here would make that guarantee rest on this
   * browser being honest. */
  sendTheDraft: (body) =>
    call("/v1/chat/send-the-draft", { method: "POST", body }),

  /** The most recent runs, newest first, whole rows.
   *
   * What the panel's history overlay is drawn from. `limit` rather than every
   * run there has ever been: this is a glance at what happened lately, and the
   * console is where somebody reads a log.
   */
  rigRuns: async (limit = 12) =>
    (await call(`/v1/workflow-runs?limit=${encodeURIComponent(limit)}`)).map(
      asPanelRun,
    ),

  /** This operator's own newest runs -- `mine=true`, because a colleague's
   * mail is not theirs to be shown on Home. */
  myRuns: async (limit) =>
    (
      await call(`/v1/workflow-runs?limit=${encodeURIComponent(limit)}&mine=true`)
    ).map(asPanelRun),

  /** A fresh conversation, when somebody asks for one. */
  newThread: () => call("/v1/threads", { method: "POST" }),

  /** They said yes: let the withheld write out.
   *
   * `call`, not a hand-rolled `fetch`, and that is the whole fix. The backend
   * reads which browser tapped through `asking_device`, which wants
   * `?device_id=` in the query and `X-Device-Secret` in the headers TOGETHER --
   * and `call` is already the one place the second of those is built. Sending
   * neither, which is what `rigHeaders()` and a `device_id` body did, is not a
   * refusal: `asking` resolves to nobody, the row records `approved_by = None`,
   * and the check that a browser only answers for the run it is driving is
   * skipped entirely, because it can only bind a caller that names a browser.
   * A live warehouse write, let out by nobody, on the door whose entire job is
   * recording who let it out -- and a 200, so nothing goes red. Half a pair is
   * at least a 404. Neither half is silent, which is why this call was fixed
   * before the other five.
   *
   * `/v1/workflow-runs`, not `/v1/runs`: on this host `/v1/runs` is a *skill*
   * run, keyed on a `RunId` and not on a workflow run's plain string. Phase 4b
   * moved all three of the rig's run doors and wrote the reason down in
   * `workflow_runs.py`'s module docstring.
   *
   * No body. The route takes none -- a `device_id` in one would be a second
   * answer to which browser is asking, one nothing checks, written into the row
   * an audit reads first.
   *
   * `deviceId` stays a parameter rather than being read from `state` here: the
   * worker already refuses a tap for any run but the one this browser is
   * driving, and it reads the id to do it.
   */
  rigApprove: (runId, deviceId) =>
    call(
      `/v1/workflow-runs/${encodeURIComponent(runId)}/approve?device_id=${encodeURIComponent(deviceId)}`,
      { method: "POST" },
    ),

  /** One skill, for the name and the shape of the version being run. */
  skill: (skillId) => call(`/v1/skills/${encodeURIComponent(skillId)}`),

  /** The person this ran for says the result was wrong -- reached by pressing
   * "Undo that" or "It's wrong, I'll fix it", things they wanted anyway,
   * which is why it can be trusted the way a survey answer could not be. See
   * `panel.js`'s `undoRun` and `wasWrong`. */
  runWrong: (runId, because) =>
    call(`/v1/runs/${encodeURIComponent(runId)}/wrong`, {
      method: "POST",
      body: { because },
    }),

  // The mining pipeline's six calls were here -- the candidate list, the two
  // teach routes, the join answer, the dismissal and the sentence resolver.
  // Every one of them served an offer to teach a SKILL from recordings, and
  // this deployment runs the rig, whose jobs arrive with their steps. The
  // routes are still on the backend, where the console uses them.

  /** This operator's running conversation, started if they have none. */
  currentThread: () => call("/v1/threads/current"),

  /** One chat by id: the chat a question was asked in, which "Answer it"
   * opens. */
  thread: (threadId) => call(`/v1/threads/${encodeURIComponent(threadId)}`),

  /** The chats this operator was asked a question in, newest first, whole. A
   * question from a mail or a short run is asked in one of these, never in
   * the conversation `currentThread` answers with. */
  askedThreads: () => call("/v1/threads/asking"),

  /** One sentence, through the one door that decides what kind it is.
   *
   * The backend answers `{kind: "job"|"lookup"}` -- an instruction becomes an
   * offer somebody presses, a question is gone and looked up. The rule that
   * decides lives there and not here on purpose: a rule with a copy in two
   * languages drifts on one of them. */
  ask: (said) => call("/v1/ask", { method: "POST", body: { said } }),

  /** Keep one password, so a run can type it without anybody recording it.
   *
   * The whole reason this exists in the extension: the person who has to
   * supply it is standing in a warehouse with this panel open. They have no
   * console, no shell and no reason to know what a vault key is, so a design
   * where a password is stored by a curl command is a design where it is
   * never stored.
   *
   * Nothing keeps it on this side. It is read out of the field, sent, and the
   * field is cleared -- it is never written to `chrome.storage`, never logged,
   * and what comes back is the key it was stored under, never the value.
   */
  keepSecret: ({ system, field, value }) =>
    call("/v1/secrets", {
      method: "PUT",
      body: { system, field, value },
      asDevice: false,
    }),

  /** The same password, for the next run and nothing after it.
   *
   * "Just this once": held in the deployment's memory, handed to the step
   * that types it, and forgotten -- never in the vault, so there is nothing
   * to rotate and nothing to delete. The operator signing into a system whose
   * credential does not belong in this deployment gives it this way.
   *
   * Nothing keeps it on this side either, exactly as above.
   *
   * `run_id` is the run the card was drawn for: the backend binds the hold
   * to it, so a password lent here can only ever reach that run and not a
   * different one racing to ask first. */
  holdSecretOnce: ({ system, field, value, runId }) =>
    call("/v1/secrets/once", {
      method: "POST",
      body: { system, field, value, run_id: runId },
      asDevice: false,
    }),

  /** Fires waiting on a person: a rule went off and asked before it ran.
   *
   * Read by the panel as well as the console, because the panel is where the
   * operator IS. A rule that fired on the page in front of them and then
   * waited in another tab is, from where they are standing, a rule that did
   * nothing -- which is exactly what one of them reported.
   */
  waiting: () => call("/v1/confirmations"),

  /** Yes, on one of those. The run starts with THIS person's name on it, not
   * the name of whoever made the rule. */
  approveWaiting: (confirmationId) =>
    call(`/v1/confirmations/${encodeURIComponent(confirmationId)}/approve`, {
      method: "POST",
    }),

  declineWaiting: (confirmationId) =>
    call(`/v1/confirmations/${encodeURIComponent(confirmationId)}/decline`, {
      method: "POST",
    }),

  /** The pages this browser offers a job on, and the values to offer it with.
   *
   * Asked for separately from the watches rather than as "this browser's
   * rules": a watch is matched against a mail, an arrival against the page in
   * front of somebody. Both only ever offer; the press starts. */
  arrivals: (deviceId) =>
    call(`/v1/agents/${encodeURIComponent(deviceId)}/arrivals`),

  /** "Do this here": the rule itself, written down.
   *
   * An ordinary trigger, which is why there is no special door for it -- the
   * kind and the page are what make it one. `authorized_by` is true because
   * the operator is standing there saying so, and the backend takes the name
   * off the credential rather than off this body.
   */
  makeArrival: ({ workflow_id, device_id, page, values }) =>
    call("/v1/triggers", {
      method: "POST",
      body: {
        workflow_id,
        device_id,
        kind: "arrival",
        arrival: { page },
        parameters: values || {},
        authorized_by: true,
      },
    }),

  /** One question, asked of every system that could answer it.
   *
   * Straight at the lookup door rather than through `/v1/ask`: this is used
   * where the sentence is already known to be a question -- a watch that asks
   * read it out of a mail -- and running the deciding rule over it again could
   * only disagree with the trigger the operator set up. */
  lookup: (question) =>
    call("/v1/lookups", { method: "POST", body: { question } }),

  /** Say something into it. Answers with the whole thread, which is why the
   * panel re-renders from the reply rather than appending locally. */
  say: (threadId, text, answering) =>
    call(`/v1/threads/${encodeURIComponent(threadId)}/messages`, {
      method: "POST",
      body: answering ? { text, answering } : { text },
    }),

  /** "Undo that": a skill's reversal, run by the backend in a browser it
   * owns -- no device, so never this one. `version` is the one the reversal
   * was checked at, and the backend runs exactly that. `authorized_by` is the
   * press: the backend reads who from the credential, never the body. */
  runSkill: (skillId, parameters, version) =>
    call(`/v1/skills/${encodeURIComponent(skillId)}/runs`, {
      method: "POST",
      body: { parameters, version, authorized_by: "the operator's press" },
    }),

  /** Ask the backend to stop a skill run the operator is watching.
   *
   * The Stop button. The backend drives the run, so stopping it is the
   * backend's to do; this browser only carries the press.
   *
   * A 409 is swallowed, and only a 409. That is the backend saying there was
   * nothing left to stop -- the run already ended, or it is not one this
   * process drives -- and pressing Stop as a run finishes is an ordinary race,
   * not a fault. Reporting it turned "your run is stopping" into "the run
   * could not be told: that run already succeeded", which is a stop control
   * raising an alarm about a run that had already stopped: louder than the
   * silence it replaced and no more true. Everything else still throws, so a
   * backend this browser genuinely cannot reach -- a run still stepping
   * somewhere with nobody able to say so -- reaches the operator who just
   * pressed Stop.
   *
   * The decision lives here rather than in the worker's message handler
   * because this file is importable on its own; `service-worker.js` registers
   * chrome listeners the moment it loads and cannot be exercised in a test. */
  stopRun: async (runId) => {
    try {
      return await call(`/v1/runs/${encodeURIComponent(runId)}/stop`, {
        method: "POST",
      });
    } catch (error) {
      if (error.status === 409) return null;
      throw error;
    }
  },

  /** What this tenant has watched, noticed and done over the last `days`.
   *
   * The panel asks for one day, to say what was done over the ledger. The
   * route reads `days` and nothing else: a `since` sent here was ignored and
   * the line counted a week. Counted
   * from rows somebody can open rather than tallied in the browser: a figure a
   * person repeats to their manager has to be one an auditor can reach. */
  summary: (days) => call(`/v1/analytics/summary?days=${Number(days) || 1}`),

  /** The operator deleting their own evidence, from their own devices, for the
   * tenant on their credential. Answers with what went. */
  forget: (since) =>
    call(`/v1/observations?since=${encodeURIComponent(since)}`, {
      method: "DELETE",
    }),
};
