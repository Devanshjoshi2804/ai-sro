// Isolated-world relay for gestures the page-realm recorder produced.
//
// recorder.generated.js runs in the page's realm (it needs the application's
// framework globals to identify a control), so it cannot reach chrome.* to
// send anything. It dispatches `sro:gesture` instead and this forwards it.
//
// The service worker decides whether the gesture is kept: pause, an
// administrator's pause, and the host policy are all checked there, because a
// content script already injected into an open tab keeps running after the
// registration that put it there is withdrawn.
(() => {
  // One relay per world, asked the way `network.js` asks it.
  //
  // This file used to have no guard at all, and its neighbour's comment said
  // why it did not need one: its top-level `const` threw on a second
  // execution in the same world, so the second copy died before it could add
  // a listener. That is a SyntaxError used as a correctness mechanism, and it
  // worked -- at the price of an uncaught error every time the worker
  // re-injects into a tab that already has us. Measured on the deployment
  // 2026-09-21: forty of them in the extension's error list, one per
  // re-injection per frame, all reading `Identifier 'MAX_GESTURE_CHARS' has
  // already been declared`.
  //
  // `injectInto` re-runs these files on every already-open watched tab -- on a
  // policy refresh, on a reload, on a press of "watch" -- and its own
  // docstring claimed "Chrome does not run a file it has already put in a
  // frame". That is true of a REGISTERED content script and false of
  // `executeScript`, which runs the file every time it is called.
  //
  // So: the same question `network.js` asks, for the same two reasons. A plain
  // "already installed" flag would be wrong -- after an extension reload the
  // copy in residence is orphaned, its `chrome.runtime` is gone, it can
  // forward nothing, and a flag it had set would keep the live replacement
  // out. Asking whether the copy in residence can still reach the worker
  // answers both cases with one question.
  if (window.__sroRelayingGestures?.()) return;
  window.__sroRelayingGestures = () => Boolean(chrome.runtime?.id);

  const MAX_GESTURE_CHARS = 128 * 1024;

  /** Whether this copy can still talk to the worker.
   *
   * An orphaned content script -- one whose extension was reloaded under it --
   * throws `Extension context invalidated` from `sendMessage`, SYNCHRONOUSLY,
   * so a `.catch()` on the returned promise never sees it. Measured on the
   * same deployment, and it is most of the rest of that error list.
   *
   * It cannot report this: there is nobody left to report it to. It goes
   * quiet, which is what `injectIntoWatched` exists to notice and repair.
   */
  const alive = () => Boolean(chrome.runtime?.id);

  const tell = (message) => {
    if (!alive()) return undefined;
    try {
      return chrome.runtime.sendMessage(message).catch(() => undefined);
    } catch {
      // The context died between the check and the call. Nothing to do and
      // nobody to tell.
    }
  };

  window.addEventListener("sro:gesture", (event) => {
    const json = event.detail;
    // Any script in the page can dispatch this event, so nothing here trusts
    // the payload: it is size-capped and shape-checked before it is forwarded,
    // and the worker re-checks the policy against the frame it came from.
    if (typeof json !== "string" || json.length > MAX_GESTURE_CHARS) return;

    let gesture;
    try {
      gesture = JSON.parse(json);
    } catch {
      return;
    }
    if (
      !gesture ||
      typeof gesture !== "object" ||
      typeof gesture.kind !== "string"
    )
      return;

    // A gesture the worker does not keep -- paused, an unwatched tab, a tab
    // running a job -- must not lend its target's state to the next one the
    // recorder records. Only an explicit `ok: true` counts as kept.
    tell({ kind: "gesture", gesture, frameUrl: location.href })?.then((reply) => {
      if (reply?.ok !== true)
        window.dispatchEvent(new CustomEvent("sro:dropped", { detail: gesture.ref }));
    });
  });

  tell({ kind: "content-ready", url: location.href });
})();
