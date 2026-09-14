// Every call to the backend. See docs/14-extension-protocol.md.

import { state } from "./state.js";

export class ApiError extends Error {
  // `where` is the call that failed, as "METHOD /path". A backend that answers
  // 500 with no body used to surface in the panel as the bare words "HTTP 500",
  // which says nothing an operator or a log reader can act on -- not which of
  // the dozen calls this extension makes had failed, so not whether the
  // recording, the run, or the registration was the thing that broke.
  constructor(status, problem, where = "") {
    super(problem?.detail || problem?.title || `HTTP ${status}${where ? ` from ${where}` : ""}`);
    this.status = status;
    this.problem = problem;
    this.where = where;
  }
}

async function call(path, { method = "GET", body, form, signal, asDevice = true } = {}) {
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
    body: form !== undefined ? form : body === undefined ? undefined : JSON.stringify(body),
  });

  if (response.status === 401) {
    // The same rule the console follows: a credential that is not accepted is
    // dropped, so the operator lands back on the paste screen instead of every
    // later call failing quietly.
    await state.setToken("");
    throw new ApiError(401, { detail: "that credential was not accepted" });
  }
  if (!response.ok) {
    throw new ApiError(response.status, await response.json().catch(() => null), `${method} ${path}`);
  }
  return response.status === 204 ? null : response.json();
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

  observations: (batch) => call("/v1/observations", { method: "POST", body: batch }),

  /** A screenshot or an oversized body, uploaded beside the batch it
   * illustrates. `form` carries device_id, batch_id, kind, file and the
   * frame_index that says which gesture it followed. */
  artifact: (form) => call("/v1/observations/artifacts", { method: "POST", form }),

  policy: () => call("/v1/agents/policy"),

  /** What this browser is watching its operator's mail for. Asked for here
   * because a watch is evaluated in the browser that has the mailbox open and
   * nowhere else -- no mail is ever sent to the backend, so the rule comes
   * the other way. */
  watches: (deviceId) => call(`/v1/agents/${encodeURIComponent(deviceId)}/watches`),

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

  /** Start a demonstration this browser will fill. Nothing is opened on the
   * server: the operator is already in front of the system. */
  startRecording: (deviceId, label) =>
    call("/v1/recordings", { method: "POST", body: { device_id: deviceId, label } }),

  /** Seal it. The backend assembles the frames from what this browser
   * uploaded, so everything must have gone up before this is called. */
  finishRecording: (recordingId, abandonReason = null) =>
    call(`/v1/recordings/${encodeURIComponent(recordingId)}/finish`, {
      method: "POST",
      // A reason means abandon rather than seal. The evidence is kept either
      // way -- what changes is that nothing will be induced from it.
      body: abandonReason ? { abandon_reason: abandonReason } : {},
    }),

  /** One run, for the panel to say what is happening in this browser.
   *
   * The worker knows a run is driving a tab and knows its id; what it is called,
   * which rung it is on and how far through it is are the run's own record. */
  run: (runId) => call(`/v1/runs/${encodeURIComponent(runId)}`),

  /** A workflow run this browser is performing, in the panel's vocabulary.
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
  rigRun: async (runId) => {
    const run = await call(`/v1/workflow-runs/${encodeURIComponent(runId)}`);
    return {
      id: run.id,
      source: "rig",
      status: run.outcome,
      steps: (run.steps || []).map((step) => ({
        index: step.order,
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
  },

  /** Stop a workflow run this browser is driving. It takes effect at the next
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
    call(`/v1/workflow-runs/${encodeURIComponent(runId)}/abort`, { method: "POST" }),

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
      const query = deviceId ? `?device_id=${encodeURIComponent(deviceId)}` : "";
      return (await call(`/v1/shapes${query}`)).shapes || [];
    } catch {
      return [];
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
      await call(`/v1/offers${deviceId ? `?device_id=${encodeURIComponent(deviceId)}` : ""}`, {
        method: "POST",
        body: rest,
      });
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
   * **Which browser to drive is a body field here, and it is the one call in
   * this file where that is right.** Everywhere else `?device_id=` names the
   * browser *asking*; a press names the browser to *drive*, and the screen
   * somebody presses on is not always it -- a supervisor's console holds the
   * tenant's credential and no extension of its own. `StartWorkflowRunRequest`
   * is where that is written down.
   *
   * No `started_by`: the backend reads who authorised it off the credential,
   * and a request that says who authorised it is a signature nobody checked. */
  rigStart: (body) => call("/v1/workflow-runs", { method: "POST", body }),

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
    call(`/v1/runs/${encodeURIComponent(runId)}/wrong`, { method: "POST", body: { because } }),

  /** Tasks this operator keeps doing on one system. The panel asks about the
   * tab it is docked beside; the host is what makes it that question. */
  candidates: (host) =>
    call(`/v1/candidates?seen_at_least=3&host=${encodeURIComponent(host)}`),

  teachCandidate: (id) =>
    call(`/v1/candidates/${encodeURIComponent(id)}/teach`, { method: "POST", body: {} }),

  /** Two candidates a person has said are one job, taught as one skill. Each
   * time the operator did both halves in a row is one demonstration of it. */
  teachTogether: (id, otherId) =>
    call(`/v1/candidates/${encodeURIComponent(id)}/teach-together`, {
      method: "POST",
      body: { other_id: otherId },
    }),

  /** What a person says two candidates are to each other. The model may only
   * ever have suggested it. */
  answerJoin: (id, otherId, kind, answer) =>
    call(`/v1/candidates/${encodeURIComponent(id)}/joins`, {
      method: "POST",
      body: { other_id: otherId, kind, answer },
    }),

  dismissCandidate: (id, reason) =>
    call(`/v1/candidates/${encodeURIComponent(id)}/dismiss`, {
      method: "POST",
      body: { reason },
    }),

  /** What a sentence asks for. Ranks the whole taught library every time --
   * there is no field on this request to restrict it to one skill, and the
   * panel does not invent one: a sentence offered against one candidate that
   * names a different taught task is answered about that task. */
  resolveIntent: (utterance) => call("/v1/intent/resolve", { method: "POST", body: { utterance } }),

  /** This operator's running conversation, started if they have none. */
  currentThread: () => call("/v1/threads/current"),

  /** One sentence, read against the jobs this tenant has been seen doing.
   *
   * Answers `{workflow_id, values, missing}` and starts nothing: the backend's
   * own words are "an offer, never a start; pressing start is a different
   * door". It spends a model call doing it -- about a fifth of a cent -- and
   * the backend bills and caps that per tenant.
   *
   * Not `resolveIntent`, which is the other resolver: that one reads an
   * utterance over the tenant's taught SKILLS with arithmetic and no model.
   * This reads it over the mined JOBS. Two vocabularies, one verb.
   */
  readChat: (utterance) => call("/v1/chat", { method: "POST", body: { utterance } }),

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
    call("/v1/secrets", { method: "PUT", body: { system, field, value }, asDevice: false }),

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
    call(`/v1/confirmations/${encodeURIComponent(confirmationId)}/approve`, { method: "POST" }),

  declineWaiting: (confirmationId) =>
    call(`/v1/confirmations/${encodeURIComponent(confirmationId)}/decline`, { method: "POST" }),

  /** The pages this browser starts a job on.
   *
   * Asked for separately from the watches rather than as "this browser's
   * rules", because the browser does two different things with them: a watch
   * is matched against a mail and OFFERS what it found, an arrival is matched
   * against the page in front of somebody and STARTS something. */
  arrivals: (deviceId) => call(`/v1/agents/${encodeURIComponent(deviceId)}/arrivals`),

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

  /** The operator arrived. No press: they pressed once, when they made the
   * rule. The url goes with it so the backend can check the rule is about the
   * page this browser says it is on -- a browser that got that wrong would
   * otherwise start a live run in somebody's window on a page nobody chose. */
  arrivalFire: (deviceId, triggerId, url) =>
    call(
      `/v1/agents/${encodeURIComponent(deviceId)}/arrivals/${encodeURIComponent(triggerId)}/fire`,
      { method: "POST", body: { url } },
    ),

  /** One question, asked of every system that could answer it.
   *
   * Straight at the lookup door rather than through `/v1/ask`: this is used
   * where the sentence is already known to be a question -- a watch that asks
   * read it out of a mail -- and running the deciding rule over it again could
   * only disagree with the trigger the operator set up. */
  lookup: (question) => call("/v1/lookups", { method: "POST", body: { question } }),

  /** Say something into it. Answers with the whole thread, which is why the
   * panel re-renders from the reply rather than appending locally. */
  say: (threadId, text) =>
    call(`/v1/threads/${encodeURIComponent(threadId)}/messages`, {
      method: "POST",
      body: { text },
    }),

  /** The press. Promotes the version a preview just showed and starts it in
   * the operator's own browser in one call -- see ADR 014 and
   * `RunFromPreview`. Refused for a looped skill with a sentence written for
   * an operator to read, which the panel shows rather than swallows.
   *
   * `version` is the one the panel rendered, and is what makes ADR 014's
   * central claim true rather than merely stated: the backend runs that
   * version and refuses the press outright where the skill has been taught
   * again since, instead of quietly running whichever version happens to be
   * newest by the time the press lands. */
  runFromPreview: (skillId, parameters, deviceId, intent, version) =>
    call(`/v1/skills/${encodeURIComponent(skillId)}/runs/from-preview`, {
      method: "POST",
      body: { parameters, device_id: deviceId, intent, version },
    }),

  /** Ask the backend to stop stepping a run it is performing in this browser.
   *
   * The other half of the Stop button. `commands.js`'s `abort` makes this
   * browser refuse every later command for the run, which is immediate and is
   * why it is still done first -- but the backend goes on stepping regardless,
   * sending each next command into a browser that answers `aborted`, so a run
   * the operator stopped kept running until it ran out of steps. Two
   * implementations of stopping, one of which the operator could not reach.
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
      return await call(`/v1/runs/${encodeURIComponent(runId)}/stop`, { method: "POST" });
    } catch (error) {
      if (error.status === 409) return null;
      throw error;
    }
  },

  /** Change what the steps still to come will run with.
   *
   * Only names the skill declares; the run refuses anything else rather than
   * recording a decision that reaches nothing. Answers with the run as it
   * stands, which is not the effect of the change -- the next step is a fresh
   * read and renders from what this saved. */
  reviseRun: (runId, values) =>
    call(`/v1/runs/${encodeURIComponent(runId)}/values`, {
      method: "POST",
      body: { values },
    }),

  /** Say something to a run that is happening.
   *
   * Kept beside it and resolved against nothing: an operator watching a run who
   * types "use the north yard address" is talking about the thing in front of
   * them, and putting that through intent matching finds some other skill and
   * offers to run it. */
  sayToRun: (threadId, runId, text) =>
    call(`/v1/threads/${encodeURIComponent(threadId)}/messages`, {
      method: "POST",
      body: { text, run_id: runId },
    }),

  /** What this tenant has watched, noticed and done since a moment.
   *
   * The panel asks for today, to say three numbers over the ledger. Counted
   * from rows somebody can open rather than tallied in the browser: a figure a
   * person repeats to their manager has to be one an auditor can reach. */
  summary: (since) =>
    call(`/v1/analytics/summary?since=${encodeURIComponent(since)}`),

  /** The operator deleting their own evidence, from their own devices, for the
   * tenant on their credential. Answers with what went. */
  forget: (since) =>
    call(`/v1/observations?since=${encodeURIComponent(since)}`, { method: "DELETE" }),
};
