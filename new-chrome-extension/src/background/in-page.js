// The half of a command that has to happen inside the page.
//
// Every function here is handed to `chrome.scripting.executeScript` as `func`,
// which serialises its source and evaluates it in the target page. That has one
// hard consequence: nothing in this file may reference anything outside its own
// body -- no imports, no module constants, no helpers next door. Each function
// is therefore self-contained and a little repetitive, and that is the price of
// running in a realm this file's module scope does not exist in.
//
// `performInPage` and the two that go with it run in the page's own realm
// (`world: "MAIN"`), because the component locator is a question only the
// application's own framework can answer -- the same reason the recorder had to
// move realms. `sendInPage` runs in the isolated world instead: it is
// same-origin with the page, so it carries the operator's cookies, but the
// page's patched `fetch` is not the one it calls, so a replayed request never
// enters the evidence plane as though the operator had made it.

/**
 * Find a control by the first locator that resolves, act on it, and say which
 * one worked.
 *
 * The strategies mirror `infrastructure/steel/ui_driver.py` deliberately: the
 * same skill, replayed on the server or in the operator's own browser, has to
 * find the same control or the two mediums are not interchangeable.
 */
export function performInPage(payload) {
  const visible = (el) => {
    if (!el || !el.getBoundingClientRect) return false;
    const rect = el.getBoundingClientRect();
    if (rect.width < 1 || rect.height < 1) return false;
    const style = window.getComputedStyle(el);
    return style.visibility !== "hidden" && style.display !== "none";
  };

  const within = (el) => {
    if (!payload.within) return true;
    try {
      const holders = window.Ext?.ComponentQuery?.query(payload.within) || [];
      return holders.some((c) => c.el?.dom?.contains(el));
    } catch {
      return true;
    }
  };

  const resolve = (locator) => {
    const wanted = locator.query;
    let found = [];
    switch (locator.strategy) {
      case "component": {
        // Ask the application, not the DOM. Its ids are assigned in render
        // order, so `#ext-gen4443` is a different control after a reload.
        const all = window.Ext?.ComponentQuery?.query(wanted) || [];
        found = all
          .filter((c) => !locator.visible_only || (c.isVisible && c.isVisible(true)))
          .map((c) => (c.inputEl || c.btnEl || c.el)?.dom)
          .filter(Boolean);
        break;
      }
      case "test_id":
        found = [...document.querySelectorAll(`[data-testid="${CSS.escape(wanted)}"]`)];
        break;
      case "role_and_name": {
        const [role, name] = wanted.split("|");
        found = [
          ...document.querySelectorAll(`[role="${CSS.escape(role)}"]`),
        ].filter((el) => (el.getAttribute("aria-label") || el.textContent || "").trim() === name);
        break;
      }
      case "text":
        // Only elements whose *own* text is the query: without that, every
        // ancestor up to <body> contains the words and the match is the page.
        found = [
          ...document.querySelectorAll("button, a, label, td, th, li, span, div, option"),
        ].filter((el) => {
          const own = [...el.childNodes]
            .filter((node) => node.nodeType === Node.TEXT_NODE)
            .map((node) => node.textContent)
            .join("")
            .trim();
          return own === wanted;
        });
        break;
      case "css_path":
        try {
          found = [...document.querySelectorAll(wanted)];
        } catch {
          found = [];
        }
        break;
      default:
        found = [];
    }
    found = found.filter(within);
    if (locator.visible_only) found = found.filter(visible);
    return found;
  };

  const type = (el, text) => {
    el.focus();
    // Through the prototype's own setter, so a framework that watches the
    // property (React and its imitators do) sees the change it is listening
    // for rather than a value that appeared without one.
    const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement : HTMLInputElement;
    const setter = Object.getOwnPropertyDescriptor(proto.prototype, "value")?.set;
    const put = (next) => (setter ? setter.call(el, next) : (el.value = next));
    put("");
    el.dispatchEvent(new Event("input", { bubbles: true }));
    // A keystroke at a time, because this WMS's combo boxes filter on them: a
    // value assigned whole leaves the picker closed and the field unvalidated,
    // which is how a replay silently fills a form nobody accepts.
    for (const character of String(text ?? "")) {
      el.dispatchEvent(new KeyboardEvent("keydown", { key: character, bubbles: true }));
      put(el.value + character);
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new KeyboardEvent("keyup", { key: character, bubbles: true }));
    }
    el.dispatchEvent(new Event("change", { bubbles: true }));
  };

  const act = (el) => {
    el.scrollIntoView({ block: "center", inline: "center" });
    switch (payload.action) {
      case "click": {
        const at = el.getBoundingClientRect();
        const where = {
          bubbles: true,
          cancelable: true,
          composed: true,
          clientX: Math.round(at.x + at.width / 2),
          clientY: Math.round(at.y + at.height / 2),
        };
        // The whole sequence, not `el.click()`: this application binds
        // `mousedown` on half its controls and never sees a bare click.
        el.dispatchEvent(new PointerEvent("pointerdown", where));
        el.dispatchEvent(new MouseEvent("mousedown", where));
        el.dispatchEvent(new PointerEvent("pointerup", where));
        el.dispatchEvent(new MouseEvent("mouseup", where));
        el.dispatchEvent(new MouseEvent("click", where));
        return null;
      }
      case "type":
        type(el, payload.value);
        return null;
      case "select": {
        if (el instanceof HTMLSelectElement) {
          const wanted = String(payload.value ?? "");
          const option = [...el.options].find(
            (o) => o.value === wanted || o.textContent.trim() === wanted,
          );
          if (!option) return `no option ${wanted}`;
          el.value = option.value;
          el.dispatchEvent(new Event("change", { bubbles: true }));
          return null;
        }
        type(el, payload.value);
        return null;
      }
      case "press": {
        const key = payload.value || "Enter";
        el.focus();
        el.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true }));
        el.dispatchEvent(new KeyboardEvent("keyup", { key, bubbles: true }));
        return null;
      }
      case "hover": {
        const at = el.getBoundingClientRect();
        const where = {
          bubbles: true,
          composed: true,
          clientX: Math.round(at.x + at.width / 2),
          clientY: Math.round(at.y + at.height / 2),
        };
        el.dispatchEvent(new PointerEvent("pointerover", where));
        el.dispatchEvent(new MouseEvent("mouseover", where));
        el.dispatchEvent(new MouseEvent("mousemove", where));
        return null;
      }
      case "scroll":
        el.scrollBy ? el.scrollBy(0, Number(payload.value) || 400) : null;
        window.scrollBy(0, Number(payload.value) || 400);
        return null;
      case "upload":
        // A file input's value cannot be set by script, by design, in every
        // browser. Saying so is the honest answer; pretending it worked would
        // have the run verify against a form that was never filled.
        return "a file cannot be attached from a page script";
      default:
        return `${payload.action} cannot be performed here`;
    }
  };

  const tried = [];
  for (const locator of payload.locators || []) {
    tried.push(`${locator.strategy}=${locator.query}`);
    let found;
    try {
      found = resolve(locator);
    } catch (error) {
      found = [];
    }
    if (!found.length) continue;

    const problem = act(found[0]);
    if (problem) {
      return {
        ok: false,
        error: { kind: "not_actionable", detail: `found the control but ${problem}` },
      };
    }
    return {
      ok: true,
      result: {
        performed: true,
        matched_by: locator.strategy,
        candidates: found.length,
        detail: null,
      },
    };
  }

  return {
    ok: false,
    error: {
      kind: "control_not_found",
      detail: `no control matched: ${tried.join(", ") || "nothing"}`,
    },
  };
}

/** Act at a point, because the gesture came from pixels rather than from a
 * control the demonstration identified. Coordinates are CSS pixels in the
 * viewport -- the same space `viewportInPage` reports, so the picture the model
 * was shown and the point it answers with measure the same thing. */
export function performAtInPage(payload) {
  const el = document.elementFromPoint(payload.x, payload.y);
  if (!el) {
    return { ok: false, error: { kind: "control_not_found", detail: "nothing at that point" } };
  }
  const where = {
    bubbles: true,
    cancelable: true,
    composed: true,
    clientX: payload.x,
    clientY: payload.y,
  };
  switch (payload.action) {
    case "click":
      el.dispatchEvent(new PointerEvent("pointerdown", where));
      el.dispatchEvent(new MouseEvent("mousedown", where));
      el.dispatchEvent(new PointerEvent("pointerup", where));
      el.dispatchEvent(new MouseEvent("mouseup", where));
      el.dispatchEvent(new MouseEvent("click", where));
      break;
    case "type": {
      el.dispatchEvent(new MouseEvent("click", where));
      // Focused explicitly, and typed into the element under the point rather
      // than into `document.activeElement`. A synthetic click does not move
      // focus -- only a trusted one does -- so reading activeElement here
      // found whatever the operator had last focused, or `<body>`: the
      // keystrokes went into some other field, or nowhere at all, and the
      // command still answered `performed`.
      if (typeof el.focus !== "function" || !("value" in el)) {
        return {
          ok: false,
          error: { kind: "not_actionable", detail: "what is at that point cannot be typed into" },
        };
      }
      el.focus();
      // Through the prototype's own setter, for the same reason `performInPage`
      // does it: a framework watching the property has to see the change.
      const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement : HTMLInputElement;
      const setter = Object.getOwnPropertyDescriptor(proto.prototype, "value")?.set;
      const put = (next) => (setter ? setter.call(el, next) : (el.value = next));
      put("");
      el.dispatchEvent(new Event("input", { bubbles: true }));
      for (const character of String(payload.value ?? "")) {
        el.dispatchEvent(new KeyboardEvent("keydown", { key: character, bubbles: true }));
        put(el.value + character);
        el.dispatchEvent(new Event("input", { bubbles: true }));
        el.dispatchEvent(new KeyboardEvent("keyup", { key: character, bubbles: true }));
      }
      el.dispatchEvent(new Event("change", { bubbles: true }));
      break;
    }
    case "press": {
      const key = payload.value || "Enter";
      // The element at the point, focused first: the same trap as `type`, and
      // an Enter delivered to `<body>` submits nothing.
      el.focus?.();
      el.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true }));
      el.dispatchEvent(new KeyboardEvent("keyup", { key, bubbles: true }));
      break;
    }
    case "scroll":
      window.scrollBy(0, Number(payload.value) || 400);
      break;
    case "hover":
      el.dispatchEvent(new PointerEvent("pointerover", where));
      el.dispatchEvent(new MouseEvent("mouseover", where));
      el.dispatchEvent(new MouseEvent("mousemove", where));
      break;
    default:
      return {
        ok: false,
        error: { kind: "not_actionable", detail: `${payload.action} cannot be done at a point` },
      };
  }
  return { ok: true, result: { performed: true, matched_by: null, candidates: 1, detail: null } };
}

/** The visible controls and where they are, plus the size of the space those
 * coordinates are in.
 *
 * Normalised to 0-1000 because that is the space the vision model answers in,
 * and measured in CSS pixels because that is the space `performAtInPage` acts
 * in. A picture measured in device pixels and a click measured in CSS pixels
 * are out by the display's scale factor, which on any retina screen is a click
 * halfway up the page. */
export function viewportInPage() {
  const width = window.innerWidth;
  const height = window.innerHeight;
  const seen = [];
  document
    .querySelectorAll("input, select, textarea, button, a, .x-grid-cell, label")
    .forEach((el) => {
      const rect = el.getBoundingClientRect();
      if (rect.width < 2 || rect.height < 2) return;
      const label = (
        el.getAttribute("aria-label") ||
        el.getAttribute("placeholder") ||
        el.textContent ||
        el.name ||
        ""
      )
        .trim()
        .slice(0, 80);
      const nx = Math.round(((rect.x + rect.width / 2) / width) * 1000);
      const ny = Math.round(((rect.y + rect.height / 2) / height) * 1000);
      if (label) seen.push(`${label}: ${nx},${ny}`);
    });
  return { url: location.href, width, height, digest: seen.slice(0, 200).join("\n").slice(0, 8000) };
}

/** Send a request from a tab that is already on that origin, so the operator's
 * own session applies -- which is why a skill can be replayed against a system
 * this deployment holds no credentials for at all.
 *
 * Runs in the isolated world. Same origin, same cookie jar, but the page's
 * patched `fetch` is not the one called here: a replayed request must not
 * arrive in the evidence plane looking like something the operator did. */
export async function sendInPage(payload) {
  const started = Date.now();
  try {
    const response = await fetch(payload.url, {
      method: payload.method || "GET",
      headers: payload.headers || {},
      body: payload.body ?? undefined,
      credentials: "include",
    });
    const headers = {};
    response.headers.forEach((value, key) => {
      headers[key] = value;
    });
    return {
      ok: true,
      result: {
        status: response.status,
        headers,
        body: (await response.text()).slice(0, 1024 * 1024),
        duration_ms: Date.now() - started,
      },
    };
  } catch (error) {
    return { ok: false, error: { kind: "unreachable", detail: String(error) } };
  }
}
