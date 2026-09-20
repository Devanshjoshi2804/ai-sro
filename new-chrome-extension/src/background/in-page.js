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
          .filter(
            (c) => !locator.visible_only || (c.isVisible && c.isVisible(true)),
          )
          .map((c) => (c.inputEl || c.btnEl || c.el)?.dom)
          .filter(Boolean);
        break;
      }
      case "test_id":
        found = [
          ...document.querySelectorAll(`[data-testid="${CSS.escape(wanted)}"]`),
        ];
        break;
      case "role_and_name": {
        const [role, name] = wanted.split("|");
        found = [
          ...document.querySelectorAll(`[role="${CSS.escape(role)}"]`),
        ].filter(
          (el) =>
            (el.getAttribute("aria-label") || el.textContent || "").trim() ===
            name,
        );
        break;
      }
      case "text":
        // Only elements whose *own* text is the query: without that, every
        // ancestor up to <body> contains the words and the match is the page.
        found = [
          ...document.querySelectorAll(
            "button, a, label, td, th, li, span, div, option",
          ),
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

  /** What the field would not take, where it took less than it was given.
   * Set by `type` and read into the reply; null when the box holds exactly
   * what it was asked to. */
  let short = null;

  /** What the field ended up holding, against what it was asked to hold.
   *
   * The browser truncates, and it does it silently and BEFORE the request.
   * `Warehouse.Description` on this deployment stops at about 28 characters
   * with no error and no warning -- observed live, §5 of the knowledge base --
   * so the shortened value is what goes into the body, comes back from the
   * read, and appears in the photograph. Every belt the run has agrees,
   * because every one of them is comparing the record to itself. The only
   * moment the difference exists is here, in the page, between what was asked
   * for and what the box will take.
   *
   * A prefix that is shorter is truncation: data is gone. Anything else --
   * trimmed spaces, a case the field normalised, a character it refused -- is
   * a difference worth saying and not worth stopping for.
   */
  const landed = (asked, got) => {
    if (got === asked) return null;
    return {
      asked: asked.length,
      kept: got.length,
      // The one distinction that matters: a shorter prefix means the field
      // took what it could and dropped the rest.
      truncated: got.length < asked.length && asked.startsWith(got),
    };
  };

  const type = (el, text) => {
    el.focus();
    // Through the prototype's own setter, so a framework that watches the
    // property (React and its imitators do) sees the change it is listening
    // for rather than a value that appeared without one.
    const proto =
      el instanceof HTMLTextAreaElement
        ? HTMLTextAreaElement
        : HTMLInputElement;
    const setter = Object.getOwnPropertyDescriptor(
      proto.prototype,
      "value",
    )?.set;
    const put = (next) => (setter ? setter.call(el, next) : (el.value = next));
    put("");
    el.dispatchEvent(new Event("input", { bubbles: true }));
    // A keystroke at a time, because this WMS's combo boxes filter on them: a
    // value assigned whole leaves the picker closed and the field unvalidated,
    // which is how a replay silently fills a form nobody accepts.
    for (const character of String(text ?? "")) {
      el.dispatchEvent(
        new KeyboardEvent("keydown", { key: character, bubbles: true }),
      );
      put(el.value + character);
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(
        new KeyboardEvent("keyup", { key: character, bubbles: true }),
      );
    }
    el.dispatchEvent(new Event("change", { bubbles: true }));
    // Read back before the field is left, because leaving it is what commits
    // whatever it decided to keep.
    short = landed(String(text ?? ""), String(el.value ?? ""));
    // And then LEFT, which is when a field commits.
    //
    // A framework keeps its own value and takes the DOM's when the field is
    // left -- ExtJS does, and it is not alone. Typing without leaving fills
    // the box on the screen and not the model behind it, so the form looks
    // right to a person and to a photograph, and the application validates
    // the empty value it still holds.
    //
    // Measured on the deployment, 2026-09-17 at 23:40: `run_6ddc89d5` typed
    // GT2, the screen showed GT2, and the Save came back "a validation error
    // on Customer Type". A person never hits this because clicking the next
    // control blurs the last one; a synthetic click does not move focus, so
    // nothing here ever left the field.
    el.blur();
    // `blur()` fires these natively, and dispatching them costs nothing and
    // covers a field whose own `blur` has been overridden -- which is a thing
    // component libraries do.
    el.dispatchEvent(new FocusEvent("focusout", { bubbles: true }));
    el.dispatchEvent(new FocusEvent("blur"));
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
        el.dispatchEvent(
          new KeyboardEvent("keydown", {
            key,
            bubbles: true,
            cancelable: true,
          }),
        );
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

    // A probe looks and does not touch.
    //
    // The control may be in any frame of the page, so the search runs in all of
    // them -- and a search that acted where it looked would click in every frame
    // that happened to match. So the frames answer where the control is, the
    // worker picks one, and only that frame is asked to act.
    if (payload.probe) {
      return {
        ok: true,
        result: {
          performed: false,
          probed: true,
          matched_by: locator.strategy,
          candidates: found.length,
        },
      };
    }

    // What this control IS, so the job can be told and stop re-deriving it.
    //
    // A step whose recorded identity has rotted is found by a rung further
    // down -- text, a css path, a point on a picture -- and until now that
    // discovery lived for exactly one command. The next run climbed the same
    // ladder and paid for the same model calls to reach the same control.
    // Measured on the deployment, 2026-09-17: the rung that looks at a picture
    // worked out "Customer Types is under Partners" three times in one
    // afternoon and the job knew no more at the end of it than at the start.
    const naming = (el) => ({
      tag: (el.tagName || "").toLowerCase(),
      name: (
        el.getAttribute("aria-label") ||
        el.getAttribute("title") ||
        el.getAttribute("name") ||
        (el.innerText || "").trim()
      ).slice(0, 80),
      item_id: (el.getAttribute("data-itemid") || el.id || "").slice(0, 80),
    });

    const problem = act(found[0]);
    if (problem) {
      return {
        ok: false,
        error: {
          kind: "not_actionable",
          detail: `found the control but ${problem}`,
        },
      };
    }
    return {
      ok: true,
      result: {
        performed: true,
        matched_by: locator.strategy,
        candidates: found.length,
        detail: null,
        // The locator that actually worked, for the job to keep.
        matched: { strategy: locator.strategy, query: locator.query },
        control: naming(found[0]),
        // What the box would not take. Null on every step that is not a type
        // and on every field that took what it was given. See `landed`: this
        // is the only moment the difference between what was asked for and
        // what the warehouse will hold actually exists.
        short,
      },
    };
  }

  // Defined HERE, inside the function that is injected, and this is why.
  //
  // `chrome.scripting.executeScript({func})` serialises that function and
  // nothing else: a helper sitting beside it in this module does not exist in
  // the page. Calling one throws a ReferenceError there, and since Chrome 117
  // the promise RESOLVES with `{result: undefined, error}` -- so a call that
  // blew up arrives at the run as no answer at all.
  //
  // Measured on the deployment across 2026-09-16 and 17: every UI step ever
  // attempted on the warehouse host failed with "the page did not answer",
  // and the only one that ever held was on a mailbox. The difference was not
  // the page. On the mailbox a locator MATCHED, so this line was never
  // reached; on the warehouse nothing matched, the near-miss report was asked
  // for, and the report is what exploded. The step that was meant to explain
  // the failure was the failure.
  const nearMisses = (payload_) => {
    const wanted = (payload_.locators || [])
      .map((locator) =>
        String(locator.query || "")
          .split("|")
          .pop(),
      )
      .filter(Boolean)
      .map((one) => one.toLowerCase());
    const seen = [];
    for (const el of document.querySelectorAll(
      "button, a[href], input, select, textarea, [role=button], [role=link], [role=tab]",
    )) {
      const name = (
        el.getAttribute("aria-label") ||
        el.getAttribute("title") ||
        el.getAttribute("placeholder") ||
        el.getAttribute("name") ||
        (el.innerText || "").trim()
      ).slice(0, 60);
      if (!name) continue;
      const said = name.toLowerCase();
      // A near miss and not a catalogue: something the step's own words are
      // part of, or that is part of them.
      if (!wanted.some((one) => said.includes(one) || one.includes(said)))
        continue;
      seen.push({ tag: el.tagName.toLowerCase(), name });
      if (seen.length === 5) break;
    }
    return seen;
  };
  const nearby = nearMisses(payload);
  // Said in the DETAIL as well as the field, because the detail is what
  // travels: the socket adapter keeps a reply's `kind` and `detail` and drops
  // everything else, and the detail is what reaches the run's own record and
  // the model asked to rescue the step.
  const also = nearby.length
    ? `; the page has ${nearby.map((one) => `${one.tag} "${one.name}"`).join(", ")}`
    : "";
  return {
    ok: false,
    error: {
      kind: "control_not_found",
      detail: `no control matched: ${tried.join(", ") || "nothing"}${also}`,
      // What the page DOES have where the step was looking.
      //
      // "no control matched: role_and_name=button|Save, css_path=..." says
      // what was tried and nothing about what is there, which is the fact a
      // person reading the run -- or the model asked to rescue the step --
      // has to have. A screen whose Save became "Save and close" reads as a
      // screen with no Save at all.
      //
      // Deliberately not acted on here. A near miss is evidence, and this
      // extension does not get to decide that a control with a different name
      // is the one the operator used: `repair_drift` in the backend already
      // settles that question from verified runs that agree more than once,
      // and never from one page's guess.
      nearby,
    },
  };
}

/** Act at a point, because the gesture came from pixels rather than from a
 * control the demonstration identified. Coordinates are CSS pixels in the
 * viewport -- the same space `viewportInPage` reports, so the picture the model
 * was shown and the point it answers with measure the same thing. */
export function performAtInPage(payload) {
  /** What the field would not take. See `landed` in `performInPage`: the same
   * rule, and the same reason it can only be known here. */
  let shortAt = null;
  const el = document.elementFromPoint(payload.x, payload.y);
  if (!el) {
    return {
      ok: false,
      error: { kind: "control_not_found", detail: "nothing at that point" },
    };
  }
  // A point inside a frame lands on the <iframe> itself from this document:
  // the events below would fire on the frame element and reach nothing, and
  // the answer would still say performed. The control is in a document this
  // script is not running in, which is a control it did not find.
  if (el.tagName === "IFRAME" || el.tagName === "FRAME") {
    // The control is in a document this script is not running in. Firing the
    // events here would hit the frame element, reach nothing, and report
    // `performed` -- so instead this says WHERE, and the worker asks that
    // frame the same question with the point moved into its coordinates.
    //
    // Measured on the deployment, 2026-09-17: the rung that looks at a picture
    // finally pointed at a control and got "that point is inside a frame". The
    // warehouse application runs in one, so every point in the picture lands
    // on the frame element from the top document -- which made the picture
    // rung useless on the one system it exists for.
    const box = el.getBoundingClientRect();
    return {
      ok: false,
      error: {
        kind: "point_in_a_frame",
        detail: "that point is inside a frame",
        // What the worker needs to ask the frame itself: where the frame sits
        // in this document, and what it is showing.
        frame: {
          src: el.src || "",
          left: Math.round(box.left),
          top: Math.round(box.top),
          width: Math.round(box.width),
          height: Math.round(box.height),
        },
      },
    };
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
          error: {
            kind: "not_actionable",
            detail: "what is at that point cannot be typed into",
          },
        };
      }
      el.focus();
      // Through the prototype's own setter, for the same reason `performInPage`
      // does it: a framework watching the property has to see the change.
      const proto =
        el instanceof HTMLTextAreaElement
          ? HTMLTextAreaElement
          : HTMLInputElement;
      const setter = Object.getOwnPropertyDescriptor(
        proto.prototype,
        "value",
      )?.set;
      const put = (next) =>
        setter ? setter.call(el, next) : (el.value = next);
      put("");
      el.dispatchEvent(new Event("input", { bubbles: true }));
      for (const character of String(payload.value ?? "")) {
        el.dispatchEvent(
          new KeyboardEvent("keydown", { key: character, bubbles: true }),
        );
        put(el.value + character);
        el.dispatchEvent(new Event("input", { bubbles: true }));
        el.dispatchEvent(
          new KeyboardEvent("keyup", { key: character, bubbles: true }),
        );
      }
      el.dispatchEvent(new Event("change", { bubbles: true }));
      // Read back before the field is left, because leaving it is what
      // commits whatever the box decided to keep. The browser truncates
      // silently and BEFORE the request, so this is the only moment the
      // difference exists -- see `landed` in `performInPage`.
      {
        const asked = String(payload.value ?? "");
        const got = String(el.value ?? "");
        shortAt =
          got === asked
            ? null
            : {
                asked: asked.length,
                kept: got.length,
                truncated: got.length < asked.length && asked.startsWith(got),
              };
      }
      // And left, so the framework behind the box takes the value. See the
      // same lines in the locator path's `type`.
      el.blur();
      el.dispatchEvent(new FocusEvent("focusout", { bubbles: true }));
      el.dispatchEvent(new FocusEvent("blur"));
      break;
    }
    case "press": {
      const key = payload.value || "Enter";
      // The element at the point, focused first: the same trap as `type`, and
      // an Enter delivered to `<body>` submits nothing.
      el.focus?.();
      el.dispatchEvent(
        new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true }),
      );
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
        error: {
          kind: "not_actionable",
          detail: `${payload.action} cannot be done at a point`,
        },
      };
  }
  return {
    ok: true,
    result: {
      performed: true,
      matched_by: null,
      short: shortAt,
      candidates: 1,
      detail: null,
      // What the point turned out to be. This is the expensive discovery --
      // a model looked at a picture to find it -- and naming it is what lets
      // the next run find it with a locator instead.
      control: {
        tag: (el.tagName || "").toLowerCase(),
        name: (
          el.getAttribute("aria-label") ||
          el.getAttribute("title") ||
          el.getAttribute("name") ||
          (el.innerText || "").trim()
        ).slice(0, 80),
        item_id: (el.getAttribute("data-itemid") || el.id || "").slice(0, 80),
      },
    },
  };
}

/** The visible controls and where they are, plus the size of the space those
 * coordinates are in.
 *
 * Normalised to 0-1000 because that is the space the vision model answers in,
 * and measured in CSS pixels because that is the space `performAtInPage` acts
 * in. A picture measured in device pixels and a click measured in CSS pixels
 * are out by the display's scale factor, which on any retina screen is a click
 * halfway up the page. */
/** How big the screen is and where it is, and nothing else.
 *
 * The cheap half of `viewportInPage`, for when the whole of it cannot be had:
 * three property reads, no layout, no selector. The picture is what the rung
 * that looks actually needs -- the digest beside it is a help, and a help that
 * costs the command its deadline is not one.
 */
export function screenSizeInPage() {
  return {
    url: location.href,
    width: window.innerWidth,
    height: window.innerHeight,
    digest: "",
  };
}

export function viewportInPage() {
  // Bounded, because this used to walk the whole document and the document is
  // a warehouse grid.
  //
  // `getBoundingClientRect` forces layout, and it was called on every match of
  // a selector that includes `.x-grid-cell` -- tens of thousands of cells on a
  // Blue Yonder grid, each one a synchronous reflow -- and then 200 of the
  // answers were kept and the rest thrown away. Measured on the deployment,
  // 2026-09-17 at 17:30: `run_0c3bd2ae` step 2 failed
  // `no screen to look at: timeout: the browser did not answer within 20s`,
  // and the same timeout had been read as three different faults across the
  // afternoon -- a refused screen, a tab that was not visible, my own console
  // tab stealing focus. None of them. The page simply could not be measured
  // in the time the run was willing to wait.
  //
  // Two limits and they are different limits. `K_LOOKED_AT` bounds the WORK --
  // how many elements are measured at all, which is what costs the time.
  // `K_NAMED` bounds the ANSWER, and was the only one here before.
  const K_LOOKED_AT = 2000;
  const K_NAMED = 200;
  const width = window.innerWidth;
  const height = window.innerHeight;
  // Where this document sits in the picture the model is shown.
  //
  // The warehouse application runs in a frame -- `performAtInPage` learned
  // that the hard way -- and a frame measures itself from its own top left.
  // Names taken from inside it were being reported as though the frame were
  // the window, which puts a control a hundred pixels below the nav bar at the
  // very top of a picture where the nav bar is.
  //
  // `frameElement` is readable only from a same-origin parent. A frame from
  // somewhere else keeps its own coordinates, which is the best that can be
  // had from inside it and is still better than no names at all.
  let dx = 0;
  let dy = 0;
  let acrossX = width;
  let acrossY = height;
  try {
    const frame = window !== window.top ? window.frameElement : null;
    if (frame) {
      const box = frame.getBoundingClientRect();
      dx = box.left;
      dy = box.top;
      acrossX = window.parent.innerWidth || width;
      acrossY = window.parent.innerHeight || height;
    }
  } catch {
    // A frame whose parent is somewhere else. Its own viewport it is, then.
  }
  const seen = [];
  // A dropdown's items are none of these.
  //
  // Measured on the deployment 2026-09-19: `Delete a Customer Type` failed
  // five times running on "Opens the filter dropdown", every one of them with
  // the control FOUND and pressed -- the screen belt read a digest with the
  // portal's top bar in it and concluded nothing had opened. ExtJS floats its
  // combo list as a `div` of `li`s appended to the body, and not one of them
  // is an input, a button or a link, so no budget and no walk order could ever
  // have described the thing the step exists to open.
  //
  // By ARIA role first, which is the web's own way of saying "this is a thing
  // to choose" -- and `.x-boundlist-item` beside it for the same reason
  // `.x-grid-cell` is already here: the one application this system is pointed
  // at renders its lists before it labels them.
  const all = document.querySelectorAll(
    "input, select, textarea, button, a, .x-grid-cell, label," +
      " [role=option], [role=menuitem], [role=treeitem], [role=tab], .x-boundlist-item",
  );
  // What the page is SAYING, before what it is offering.
  //
  // The digest was names of controls and nothing else, so a page whose whole
  // message was a dialog produced a digest with the dialog's buttons in it and
  // not a word of what the dialog said. Measured on the deployment, 2026-09-17
  // at 23:05: `run_21b92747` filled the form on the page and the Save came
  // back "An exception dialog appeared and the record has not been created" --
  // the model's paraphrase, because the screen text it was given had the
  // dialog's OK button and none of its sentence.
  //
  // By ARIA role, which is the web's own way of saying "this is the page
  // talking to you" and belongs to no vendor. First in the digest because a
  // message is the thing a reader wants first, and a handful of elements, so
  // it costs nothing against the budget below.
  for (const el of document.querySelectorAll(
    "[role=alert], [role=alertdialog], [role=status], [aria-live=assertive], [aria-live=polite]",
  )) {
    const says = (el.innerText || el.textContent || "")
      .trim()
      .replace(/\s+/g, " ");
    if (says) seen.push(`says: ${says.slice(0, 300)}`);
    if (seen.length >= K_NAMED) break;
  }
  // Both ends of the document, not the first two hundred elements of it.
  //
  // A page is written header-first, so walking it in order spends the whole
  // budget on the application's own chrome. Measured on the deployment,
  // 2026-09-17 at 23:40: the digest for a screen showing an error dialog was
  // "Search: 865,18 Workstation: 681,18 SG: 625,18 ..." -- the top bar, and
  // not one word of the dialog the run had just failed on.
  //
  // A dialog is appended to the body, so it is at the END. Half the budget
  // from each end catches both what the screen is FOR and what it is saying,
  // and neither is reachable by reading the other.
  // The same budget, taken alternately from each end.
  //
  // Not front-then-back: the ANSWER is capped too, and two hundred names of
  // header controls fill it before the walk ever reaches the other end. Taking
  // one from each end in turn means a page longer than either budget is still
  // described from both, which is the whole point.
  const order = [];
  for (
    let front = 0, back = all.length - 1;
    front <= back;
    front += 1, back -= 1
  ) {
    if (order.length >= K_LOOKED_AT) break;
    order.push(front);
    if (back !== front && order.length < K_LOOKED_AT) order.push(back);
  }
  for (const n of order) {
    if (seen.length >= K_NAMED) break;
    const el = all[n];
    const rect = el.getBoundingClientRect();
    if (rect.width < 2 || rect.height < 2) continue;
    // Off the screen entirely. This is what the digest is FOR -- what the
    // operator is looking at -- and the coordinates beside each name are
    // fractions of the viewport, so a row scrolled a thousand pixels below it
    // was being described at `y: 4300` in a space that ends at 1000. Wrong as
    // well as slow.
    if (
      rect.bottom < 0 ||
      rect.top > height ||
      rect.right < 0 ||
      rect.left > width
    )
      continue;
    const label = (
      el.getAttribute("aria-label") ||
      el.getAttribute("placeholder") ||
      el.textContent ||
      el.name ||
      ""
    )
      .trim()
      .slice(0, 80);
    const nx = Math.round(((rect.x + rect.width / 2 + dx) / acrossX) * 1000);
    const ny = Math.round(((rect.y + rect.height / 2 + dy) / acrossY) * 1000);
    if (label) seen.push(`${label}: ${nx},${ny}`);
  }
  return {
    url: location.href,
    width,
    height,
    digest: seen.join("\n").slice(0, 8000),
  };
}

/** The one header this extension knows how to read live: Blue Yonder keeps
 * its write token in a page-level JS global, never in a cookie, so a
 * recording can only ever capture a value the recorder correctly redacts.
 * Runs in the MAIN world -- `Ext` is the page's own framework object, not
 * reachable from the isolated world `sendInPage` runs in -- and answers
 * `null`, never throws, when the page has no such global to read. */
export function csrfTokenInPage() {
  return window.Ext?.Ajax?.defaultHeaders?.["CSRF-ENCRYPT-TOKEN"] ?? null;
}

/** What this page marks its own XHRs with.
 *
 * Read off the page first and only then defaulted, which is the difference
 * between sending what the application sends and sending what a spec says it
 * ought to. Blue Yonder's ExtJS puts it on `Ajax.defaultHeaders` beside the
 * CSRF token; a framework that names itself instead would be sent its own
 * name, and one that sets nothing gets the value every XHR library has used
 * for twenty years.
 *
 * Not a credential, and that is why it can be defaulted at all. The recorder
 * strikes it out because it sits in `SECRET_HEADERS` beside the real ones, so
 * the recording carries a marker and not a value -- and a write that arrives
 * without it is refused by an application that expects it before it is ever
 * routed. Nothing is carried from the backend either way: the name is asked
 * for, the value is found here.
 */
export function requestedWithInPage() {
  return (
    window.Ext?.Ajax?.defaultHeaders?.["X-Requested-With"] ?? "XMLHttpRequest"
  );
}

/** Send a request from a tab that is already on that origin, so the operator's
 * own session applies -- which is why a skill can be replayed against a system
 * this deployment holds no credentials for at all.
 *
 * Runs in the isolated world. Same origin, same cookie jar, but the page's
 * patched `fetch` is not the one called here: a replayed request must not
 * arrive in the evidence plane looking like something the operator did. */
export async function sendInPage(payload) {
  // Bounded, and it says how long it took either way.
  //
  // `TypeError: Failed to fetch` is what a browser says for every one of: the
  // host did not resolve, the connection was refused, CORS refused the
  // response, and the document running this was torn down mid-request. Four
  // faults, one sentence, and no clue which -- so the one thing that tells
  // them apart, how long it took to fail, was being thrown away.
  //
  // Measured on the deployment, 2026-09-17: `run_e1ff6362` step 6 failed
  // `unreachable: TypeError: Failed to fetch`, and the only reason anybody
  // knows it stalled for 54 seconds first is that two log lines on the SERVER
  // happened to bracket it. An instant failure is a refusal; a long one is a
  // connection nobody answered. Those want different fixes.
  //
  // `timeout_ms` is the command's own where it carries one, because a call has
  // no business outliving the deadline the run is waiting on.
  const K_CALL_MS = 15_000;
  const started = Date.now();
  const control = new AbortController();
  const giveUp = setTimeout(
    () => control.abort(),
    Number(payload?.timeout_ms) || K_CALL_MS,
  );
  try {
    const response = await fetch(payload.url, {
      method: payload.method || "GET",
      headers: payload.headers || {},
      body: payload.body ?? undefined,
      credentials: "include",
      signal: control.signal,
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
    const took = Date.now() - started;
    if (control.signal.aborted) {
      return {
        ok: false,
        error: {
          kind: "unreachable",
          detail: `the system did not answer within ${took}ms`,
        },
      };
    }
    // And WHICH of the four it was, where one cheap question can say.
    //
    // The comment above lists them: the host did not resolve, the connection
    // was refused, CORS refused the response, the document was torn down. It
    // leaves out the one that is commonest in a warehouse and is not a
    // network fault at all -- the session expired, the endpoint answered 302
    // to an identity provider on another origin, and `redirect: "follow"`
    // walked the fetch across an origin boundary it is not allowed to cross.
    // Same `TypeError: Failed to fetch`, and nothing about it is unreachable.
    //
    // Measured on the deployment 2026-09-21. `GET /data/WM/wm/customerTypes`
    // answered 200 with fifty records at 18:30 and `Failed to fetch after
    // 341ms` at 20:10, with the operator's own machine reaching that exact
    // address in 12ms and being answered 302. Between the two, they had been
    // signed out. The panel said "unreachable", which sent everybody looking
    // at the network.
    //
    // Only on the failure path, and only one request: `redirect: "manual"`
    // does not follow, so a redirect comes back as an opaque response instead
    // of an exception. A run's own replayed calls keep following redirects,
    // because a POST that legitimately redirects is a POST that worked.
    // Inline, and it has to be: `executeScript` serialises this function to
    // source and evaluates it in the page, so anything it names from this
    // module does not exist where it runs. `injected.test.mjs` holds that --
    // it caught this as a `ReferenceError` on a path that only runs when
    // something has already gone wrong, which is the path nobody watches.
    //
    // `redirect: "manual"` hands back an opaque response for a redirect
    // instead of walking it to another origin and throwing. `opaqueredirect`
    // is the whole of the signal and no header of it is readable, which is
    // fine: that it redirects at all is what says the data is not there.
    //
    // Never allowed to throw. A diagnostic that can fail the thing it is
    // diagnosing is worse than no diagnostic.
    let redirected = false;
    try {
      const looked = await fetch(payload.url, {
        method: "GET",
        credentials: "include",
        redirect: "manual",
        signal: AbortSignal.timeout(4000),
      });
      redirected =
        looked.type === "opaqueredirect" ||
        (looked.status >= 300 && looked.status < 400);
    } catch {
      redirected = false;
    }
    if (redirected) {
      return {
        ok: false,
        error: {
          kind: "signed_out",
          detail:
            "that system answered with a redirect rather than data, which is" +
            " what it does when the session has gone -- sign in and ask again",
        },
      };
    }
    return {
      ok: false,
      error: {
        kind: "unreachable",
        // The elapsed time and whether the browser thinks it has a network at
        // all: the two facts that tell a refusal from a stall, and neither of
        // them costs anything to collect.
        detail:
          `${error} after ${took}ms` +
          (navigator.onLine === false ? " (this browser is offline)" : ""),
      },
    };
  } finally {
    clearTimeout(giveUp);
  }
}
