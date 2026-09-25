// Acting at a point, through the browser rather than through the page.
//
// The rung that looks at a picture answers in viewport coordinates: "the Add
// button is at (612, 214)". Every other rung answers with an element -- a
// component id, a css path, a piece of text -- and an element can be handed
// straight to `chrome.scripting.executeScript`, which is why they work.
//
// A point cannot. `executeScript` runs in a DOCUMENT, and it has to be told
// which one: `target: { tabId, frameIds: [...] }`. So a coordinate-native rung
// was being pushed through a frame-native API, and the extension had to work
// out which frame owned the pixel before it could act on it. On the one system
// this rung exists for -- a warehouse application that renders its whole self
// inside an iframe -- that lookup is the only thing standing between a correct
// point and a click, and it failed for a reason nothing in the point was wrong
// about: a frame's `src` ATTRIBUTE is the url it was CREATED with, and the
// application had routed inside it long since. Measured on the deployment,
// 2026-09-17 at 14:20: `control_not_found: that point is inside a frame this
// browser cannot reach`, on a run that was on the right page looking at the
// right button.
//
// `Input.dispatchMouseEvent` has no frame to name. It takes a point in the
// top-level viewport and the browser routes the event to whichever renderer
// owns that pixel -- same-origin, cross-origin, out-of-process, nested, it
// does not matter, because this is the same path a real mouse takes. The
// entire class of bug disappears rather than being handled.
//
// Two things come with it that the synthetic path could not have:
//
// **The events are trusted.** `isTrusted` is true, because they did not come
// from script. A synthetic click does not move focus and a widget that checks
// is entitled to ignore it; a real one is a real one.
//
// **Typing is typing.** `Input.insertText` goes through the same editing
// machinery a keyboard does, so a framework watching its own input sees what
// it expects instead of a value written through a prototype setter and an
// `input` event fired by hand.
//
// ## What it costs
//
// `chrome.debugger`, and so the "AI-SRO is debugging this browser" banner for
// as long as a command is in flight: invisible under `ExtensionInstallForcelist`,
// which is the deployment this is for, and visible on an unpacked development
// copy. It is not policy-gated -- a run acting on a page is a deliberate act
// somebody asked for, not a background convenience.
//
// Chrome allows one debugger client per tab, so an operator with DevTools open
// takes it. `pointAt` says so rather than pretending, and the caller falls back
// to the synthetic path, which is worse but is not nothing.

const PROTOCOL = "1.3";

/** Tabs this module attached itself, so it detaches only what it took.
 *
 * An attach that failed (DevTools holds the tab) is an attach that is not
 * undone: detaching would pull the floor out from under whoever holds it. */
const ours = new Set();

/** How a key is described to the browser. `text` is what makes a keypress
 * insert something; a bare keydown with no text moves a caret and types
 * nothing. Only the keys a recorded step actually presses are here -- anything
 * else is dispatched by name and does whatever the page makes of it. */
const KEYS = {
  Enter: { code: "Enter", keyCode: 13, text: "\r" },
  Tab: { code: "Tab", keyCode: 9 },
  Escape: { code: "Escape", keyCode: 27 },
  Backspace: { code: "Backspace", keyCode: 8 },
  ArrowDown: { code: "ArrowDown", keyCode: 40 },
  ArrowUp: { code: "ArrowUp", keyCode: 38 },
};

/** What is at a point, named. Runs in the frame that owns the pixel, whichever
 * that is, because CDP resolved the node before this ever sees it. */
const NAME_IT = `function () {
  const el = this instanceof Element ? this : this?.parentElement;
  if (!el) return null;
  return {
    tag: (el.tagName || "").toLowerCase(),
    name: (
      el.getAttribute("aria-label") ||
      el.getAttribute("title") ||
      el.getAttribute("name") ||
      (el.innerText || "").trim()
    ).slice(0, 80),
    item_id: (el.getAttribute("data-itemid") || el.id || "").slice(0, 80),
  };
}`;

/** Take the tab, or say we could not.
 *
 * A failed attach is not reported here: a genuine refusal shows up as the
 * first `sendCommand` throwing, which is where it is reported.
 */
async function hold(tabId) {
  if (ours.has(tabId)) return;
  try {
    await chrome.debugger.attach({ tabId }, PROTOCOL);
    ours.add(tabId);
  } catch {
    // Already attached, by DevTools. This does not own it and must not
    // detach it.
  }
}

async function letGo(tabId) {
  if (!ours.has(tabId)) return;
  ours.delete(tabId);
  await chrome.debugger.detach({ tabId }).catch(() => {});
}

const send = (tabId, method, params) =>
  chrome.debugger.sendCommand({ tabId }, method, params);

/** The element at a point, named, or null.
 *
 * Wanted for its own sake rather than to act on: the sight rung is the
 * expensive one, and what it discovers -- that the thing at (612, 214) is
 * called "Add" -- is what lets the next run find the control with a cheap
 * locator instead of another picture. `learned_from` on the server turns this
 * into `text=Add`.
 *
 * A null here is not a failure to act. The click still goes to the pixel.
 */
async function nameAt(tabId, x, y) {
  try {
    await send(tabId, "DOM.enable");
    // `DOM.getDocument` first: `getNodeForLocation` answers out of the node
    // map, and without a document there is no map to answer from.
    await send(tabId, "DOM.getDocument", { depth: 0 });
    const at = await send(tabId, "DOM.getNodeForLocation", {
      x: Math.round(x),
      y: Math.round(y),
      includeUserAgentShadowDOM: false,
    });
    if (!at?.backendNodeId) return null;
    const node = await send(tabId, "DOM.resolveNode", {
      backendNodeId: at.backendNodeId,
    });
    const objectId = node?.object?.objectId;
    if (!objectId) return null;
    const said = await send(tabId, "Runtime.callFunctionOn", {
      objectId,
      functionDeclaration: NAME_IT,
      returnByValue: true,
    });
    return said?.result?.value || null;
  } catch {
    // Naming is the optional half. A point that could not be named is still a
    // point that can be clicked, and saying nothing is better than refusing.
    return null;
  }
}

const mouse = (type, x, y, over = {}) => ({
  type,
  x: Math.round(x),
  y: Math.round(y),
  button: type === "mouseMoved" ? "none" : "left",
  buttons: type === "mousePressed" ? 1 : 0,
  clickCount: type === "mouseMoved" ? 0 : 1,
  ...over,
});

async function clickAt(tabId, x, y) {
  // Moved to, then pressed. A page that shows its button only on hover is one
  // where the press has to arrive after the pointer does, and a real mouse is
  // never anywhere else first.
  await send(tabId, "Input.dispatchMouseEvent", mouse("mouseMoved", x, y));
  await send(tabId, "Input.dispatchMouseEvent", mouse("mousePressed", x, y));
  await send(tabId, "Input.dispatchMouseEvent", mouse("mouseReleased", x, y));
}

async function key(tabId, name, type) {
  const known = KEYS[name] || {};
  await send(tabId, "Input.dispatchKeyEvent", {
    type: type === "down" && known.text ? "keyDown" : type === "down" ? "rawKeyDown" : "keyUp",
    key: name,
    code: known.code || name,
    windowsVirtualKeyCode: known.keyCode || 0,
    nativeVirtualKeyCode: known.keyCode || 0,
    ...(type === "down" && known.text ? { text: known.text } : {}),
  });
}

/** Do one thing at one point, through the browser.
 *
 * `{ ok: true, result }` in the shape `sroPage.performAt` returns, so a caller
 * can use either. `{ ok: false, error }` where the browser would not let this
 * drive the tab at all -- which is the caller's cue to try the page instead,
 * not to give up.
 */
export async function pointAt(tabId, payload) {
  const { x, y, action, value } = payload;
  await hold(tabId);
  try {
    // Named before it is pressed. A click can navigate, and a control that is
    // gone cannot say what it was called.
    const control = action === "scroll" ? null : await nameAt(tabId, x, y);
    switch (action) {
      case "click":
        await clickAt(tabId, x, y);
        break;
      case "hover":
        await send(tabId, "Input.dispatchMouseEvent", mouse("mouseMoved", x, y));
        break;
      case "scroll":
        await send(tabId, "Input.dispatchMouseEvent", {
          ...mouse("mouseWheel", x, y),
          deltaX: 0,
          deltaY: Number(value) || 400,
        });
        break;
      case "press":
        await clickAt(tabId, x, y);
        await key(tabId, value || "Enter", "down");
        await key(tabId, value || "Enter", "up");
        break;
      case "type": {
        // Clicked to put the caret in it, selected, then typed over. Select-all
        // rather than a loop of Backspace: a field with a value already in it
        // is the ordinary case on a form a run has been down before, and
        // "type" has always meant the field ends up holding this and nothing
        // else.
        await clickAt(tabId, x, y);
        await send(tabId, "Input.dispatchKeyEvent", {
          type: "keyDown",
          key: "a",
          code: "KeyA",
          windowsVirtualKeyCode: 65,
          nativeVirtualKeyCode: 65,
          // Both, because this extension does not know which platform it is
          // on and the browser ignores the modifier its platform does not use.
          // 6 == Ctrl(2) | Meta(4).
          modifiers: 6,
        });
        await send(tabId, "Input.dispatchKeyEvent", {
          type: "keyUp",
          key: "a",
          code: "KeyA",
          windowsVirtualKeyCode: 65,
          nativeVirtualKeyCode: 65,
          modifiers: 6,
        });
        // An empty value is a field being cleared, and `insertText` with ""
        // inserts nothing rather than replacing the selection.
        const typed = String(value ?? "");
        if (typed) {
          await send(tabId, "Input.insertText", { text: typed });
        } else {
          await key(tabId, "Backspace", "down");
          await key(tabId, "Backspace", "up");
        }
        // No `change` fired here on purpose. A real keyboard does not fire one
        // either -- the page fires it when the field is left, which is what
        // the next step's click does. Firing it now is the synthetic path's
        // habit, and it made forms commit a value before it had been typed in
        // full.
        break;
      }
      default:
        return {
          ok: false,
          error: {
            kind: "not_actionable",
            detail: `${action} cannot be done at a point`,
          },
        };
    }
    return {
      ok: true,
      result: {
        performed: true,
        matched_by: null,
        candidates: 1,
        detail: null,
        control,
      },
    };
  } catch (error) {
    // The tab is not ours to drive: DevTools has the one debugger slot, or the
    // tab went away mid-command. Said as a refusal the caller can route around
    // rather than as a failure of the step.
    return {
      ok: false,
      error: {
        kind: "cannot_drive_tab",
        detail: String(error?.message || error),
      },
    };
  } finally {
    await letGo(tabId);
  }
}
