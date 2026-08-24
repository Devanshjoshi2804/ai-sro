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

const MAX_GESTURE_CHARS = 128 * 1024;

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
  if (!gesture || typeof gesture !== "object" || typeof gesture.kind !== "string") return;

  chrome.runtime
    .sendMessage({ kind: "gesture", gesture, frameUrl: location.href })
    .catch(() => {});
});

chrome.runtime.sendMessage({ kind: "content-ready", url: location.href }).catch(() => {});
