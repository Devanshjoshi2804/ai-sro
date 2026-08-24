// The capture entry point: defines the binding recorder.generated.js calls,
// and proves this frame is running before that file's own listeners install.
//
// Order matters. scripts.js lists this file first in the registration, so
// `window.__sroRecord` exists before the recorder's IIFE runs and calls it --
// the same binding shape Steel's `Runtime.addBinding` gives it server-side,
// stood up here as a plain assignment instead. Both files see the same real
// `window`, isolated world or not: only declared bindings (let/const/function
// at top scope) are separated per world, an explicit `window.x = …` is not.

window.__sroRecord = (json) => {
  let gesture;
  try {
    gesture = JSON.parse(json);
  } catch {
    return; // Malformed is dropped here, the same way recorder.js drops a
    // send with no binding installed -- evidence lost is preferable to a
    // console error the operator sees on every click.
  }
  chrome.runtime
    .sendMessage({ kind: "gesture", gesture, frameUrl: location.href })
    .catch(() => {
      // The worker is asleep, or this frame is closing. MV3 wakes the worker
      // for a message it can deliver; a message with nowhere to land is not
      // worth retrying from here -- the next gesture tries again.
    });
};

chrome.runtime.sendMessage({ kind: "content-ready", url: location.href }).catch(() => {});
