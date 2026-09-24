// Which tabs are inside an OAuth/OIDC sign-in right now.
//
// Spec 5.6: a sign-in page is captured structure-only, and a page is one when
// it holds a password or one-time-code field -- which the page itself can see
// -- or when the tab is somewhere between an authorize request and the return
// to the `redirect_uri`'s origin -- which only the tab's history can say. A
// Microsoft code box (`name=otc type=tel autocomplete=off`) is the second
// kind: nothing on that page says "credential" except where the tab has been.
//
// The rule is `signInFlowAfter`, generated from `sensitivity.py` so the
// backend and Steel judge the same URLs the same way. This keeps its answer
// per tab, in storage rather than in a Map: typing a code takes longer than
// this worker lives. Every change and every question goes through `serially`,
// so a gesture asking about a tab waits for the navigation that was already
// being noted -- the listener starts the note before anything awaits.

import { signInFlowAfter } from "../content/sensitivity.module.js";
import { serially } from "./serially.js";
import { state } from "./state.js";

/** The tab went to `url`: its flow starts, carries on or ends. */
export function navigated(tabId, url) {
  return serially(async () => {
    const flows = await state.signInFlows();
    const before = flows[tabId] ?? null;
    const after = signInFlowAfter(before, url);
    if (after === before) return;
    if (after) flows[tabId] = after;
    else delete flows[tabId];
    await state.setSignInFlows(flows);
  });
}

/** Whether a page in this tab is inside a sign-in flow. */
export function inSignInFlow(tabId) {
  if (tabId === null || tabId === undefined) return Promise.resolve(false);
  return serially(async () => Boolean((await state.signInFlows())[tabId]));
}

/** The tab closed. A reused id is somebody else's page. */
export function forgetSignIn(tabId) {
  return serially(async () => {
    const flows = await state.signInFlows();
    if (!(tabId in flows)) return;
    delete flows[tabId];
    await state.setSignInFlows(flows);
  });
}
