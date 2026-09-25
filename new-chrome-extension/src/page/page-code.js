(() => {
  const REPAIR_THRESHOLD = 3;
  const REPAIR_MARGIN = 2;
  const REPAIRABLE_ACTIONS = new Set(["click", "hover", "scroll"]);
  const UNREPAIRABLE_ROLES = new Set(["checkbox", "radio", "switch", "option", "combobox"]);
  const NEAR_PX = 50;
  const GENERATED_ID = /^(ext-|gen)|\d{3,}/;
  const CANDIDATES = "input, select, textarea, button, a, [role], [tabindex]";

  const readers = (() => {
    const MAX_TEXT = 200;
    const roleOf = (el) => {
      const written = el.getAttribute("role");
      if (written) return written;
      const tag = el.tagName.toLowerCase();
      if (tag === "button") return "button";
      if (tag === "a") return el.hasAttribute("href") ? "link" : null;
      if (tag === "select") return "combobox";
      if (tag === "textarea") return "textbox";
      if (tag === "summary") return "button";
      if (tag !== "input") return null;
      const type = (el.getAttribute("type") || "text").toLowerCase();
      if (type === "checkbox") return "checkbox";
      if (type === "radio") return "radio";
      if (type === "range") return "slider";
      if (["button", "submit", "reset", "image"].includes(type)) return "button";
      if (["text", "search", "email", "tel", "url", "password", "number"].includes(type))
        return "textbox";
      return null;
    };
    const ownName = (el) => {
      const aria = (el.getAttribute("aria-label") || "").trim();
      if (aria) return aria.slice(0, MAX_TEXT);
      const by = el.getAttribute("aria-labelledby");
      if (!by) return null;
      const doc = el.ownerDocument || document;
      const said = by
        .split(/\s+/)
        .map((id) => (doc.getElementById(id) || {}).innerText || "")
        .join(" ")
        .trim();
      return said ? said.slice(0, MAX_TEXT) : null;
    };
    const nameOf = (el) => {
      const own = ownName(el);
      if (own) return own;
      if (el.labels && el.labels.length) return (el.labels[0].innerText || "").trim().slice(0, MAX_TEXT);
      const pressed = el.tagName.toLowerCase() === "input" && roleOf(el) === "button" ? el.value : "";
      const said = el.getAttribute("placeholder") || el.getAttribute("title") || el.innerText || pressed || "";
      return said.trim().slice(0, MAX_TEXT);
    };
    const landmarkRole = (el) => {
      const written = el.getAttribute("role");
      const named = ["region", "dialog", "alertdialog", "grid", "treegrid", "form"];
      if (written) return named.includes(written) ? written : null;
      const tag = el.tagName.toLowerCase();
      if (tag === "form") return "form";
      if (tag === "dialog") return "dialog";
      if (tag === "section") return "region";
      return null;
    };
    const landmarksOf = (el) => {
      const found = [];
      for (let node = el.parentElement; node && node.nodeType === 1; node = node.parentElement) {
        const role = landmarkRole(node);
        const name = role ? ownName(node) : null;
        if (role && name) found.unshift({ role, name });
      }
      return found;
    };
    const cmpOf = (el) => {
      const Ext = (el.ownerDocument?.defaultView || window).Ext;
      if (!Ext?.getCmp) return null;
      for (let node = el; node && node.nodeType === 1; node = node.parentElement) {
        const cmp = node.id && (Ext.getCmp(node.id) || Ext.getCmp(node.id.replace(/-[a-zA-Z]+El$/, "")));
        if (cmp) return cmp;
      }
      return null;
    };
    const chainOf = (el) => {
      const chain = [];
      for (let k = cmpOf(el); k && chain.length < 10; k = k.ownerCt || k.floatParent) {
        const xtype = k.getXType ? k.getXType() : k.xtype;
        if (!xtype) continue;
        chain.unshift(k.itemId && !/^ext-/.test(k.itemId) ? `${xtype}#${k.itemId}` : xtype);
      }
      return chain;
    };
    const xpathOf = (el) => {
      const parts = [];
      for (let node = el; node && node.nodeType === 1; node = node.parentElement) {
        const parent = node.parentElement;
        if (!parent) {
          parts.unshift(node.tagName.toLowerCase());
          break;
        }
        const siblings = [...parent.children].filter((c) => c.tagName === node.tagName);
        parts.unshift(`${node.tagName.toLowerCase()}[${siblings.indexOf(node) + 1}]`);
      }
      return `/${parts.join("/")}`;
    };
    const boundsOf = (el) => {
      const box = el.getBoundingClientRect();
      const view = el.ownerDocument?.defaultView || window;
      return { x: box.x + (view.scrollX || 0), y: box.y + (view.scrollY || 0), width: box.width, height: box.height };
    };
    const framePathOf = (win) => {
      const hops = [];
      const origins = (win.location && win.location.ancestorOrigins) || [];
      let depth = 0;
      for (let here = win; here.parent && here !== here.parent; here = here.parent, depth += 1) {
        const parent = here.parent;
        let index = -1;
        for (let i = 0; i < parent.frames.length; i += 1) {
          if (parent.frames[i] === here) index = i;
        }
        let url = null;
        try {
          url = here.location.href;
        } catch {
          url = depth > 0 ? origins[depth - 1] || null : null;
        }
        hops.unshift({ index, url });
      }
      return hops;
    };
    const settingOf = (el) => {
      if (["checkbox", "radio", "switch"].includes(roleOf(el))) {
        const checked = typeof el.checked === "boolean" ? el.checked : el.getAttribute("aria-checked") === "true";
        return checked ? "checked" : "unchecked";
      }
      if (el.tagName === "SELECT") {
        return [...(el.selectedOptions || [])].map((option) => option.label).join(", ") || null;
      }
      return undefined;
    };
    return { roleOf, ownName, nameOf, landmarkRole, landmarksOf, cmpOf, chainOf, xpathOf, boundsOf, framePathOf, settingOf };
  })();
  const { roleOf, ownName, nameOf, landmarkRole, landmarksOf, cmpOf, chainOf, xpathOf, boundsOf, framePathOf, settingOf } =
    readers;

  const shown = (el) => {
    const box = el.getBoundingClientRect();
    if (box.width < 1 || box.height < 1) return false;
    const style = getComputedStyle(el);
    return style.visibility !== "hidden" && style.display !== "none";
  };
  const qsa = (selector, root = document) => {
    try {
      return [...root.querySelectorAll(selector)];
    } catch {
      return [];
    }
  };
  const triggerOf = (c) => {
    const one = c.triggerEl;
    if (one?.dom) return one.dom;
    if (typeof one?.item === "function") {
      const first = one.item(0);
      if (first?.dom) return first.dom;
    }
    const named = c.triggers && Object.values(c.triggers)[0];
    return named?.el?.dom || null;
  };
  const partOf = (c, action) => {
    if (action === "click") {
      const arrow = triggerOf(c);
      if (arrow) return arrow;
    }
    return (c.inputEl || c.btnEl || c.el)?.dom;
  };
  const components = (query, win = window) =>
    (win.Ext?.ComponentQuery?.query(query) || []).filter((c) => c.isVisible?.(true));
  const ext = (query, action) => components(query).map((c) => partOf(c, action)).filter(Boolean);
  const ownText = (text) =>
    qsa("button, a, label, td, th, li, span, div, option").filter(
      (el) => [...el.childNodes].filter((n) => n.nodeType === 3).map((n) => n.textContent).join("").trim() === text,
    );
  const scopes = (landmarks) => {
    const inner = (landmarks || []).at(-1);
    if (!inner) return [document];
    return qsa("*").filter((el) => landmarkRole(el) === inner.role && ownName(el) === inner.name);
  };
  const attributeSelector = (t) => {
    const a = t.attributes || {};
    const parts = [];
    if (a.name) parts.push(`[name="${CSS.escape(a.name)}"]`);
    if (a.autocomplete) parts.push(`[autocomplete="${CSS.escape(a.autocomplete)}"]`);
    if (a.id && !GENERATED_ID.test(a.id)) parts.push(`#${CSS.escape(a.id)}`);
    if (!parts.length) return null;
    if (a.type) parts.push(`[type="${CSS.escape(a.type)}"]`);
    return `${t.tag || ""}${parts.join("")}`;
  };
  const byXpath = (xpath, doc = document) => {
    try {
      const got = doc.evaluate(xpath, doc, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
      return Array.from({ length: got.snapshotLength }, (_, i) => got.snapshotItem(i));
    } catch {
      return [];
    }
  };
  const byLearned = ({ strategy, query }, action) => {
    if (strategy === "component") return ext(query.startsWith("#") || query.includes(" ") ? query : `#${query}`, action);
    if (strategy === "role_and_name") {
      const cut = query.indexOf("|");
      const role = query.slice(0, cut);
      const name = query.slice(cut + 1);
      return qsa("*").filter((el) => roleOf(el) === role && nameOf(el) === name);
    }
    if (strategy === "test_id") return qsa(`[data-testid="${CSS.escape(query)}"]`);
    if (strategy === "text") return ownText(query);
    if (strategy === "xpath") return byXpath(query);
    return qsa(query);
  };
  const STRATEGIES = [
    ["learned", (t, p) => (p.learned ? byLearned(p.learned, p.action) : [])],
    ["component_chain", (t, p) => (t.component?.chain?.length > 1 ? ext(t.component.chain.join(" "), p.action) : [])],
    ["component", (t, p) => (t.component?.query ? ext(t.component.query, p.action) : t.component?.item_id ? ext(`#${t.component.item_id}`, p.action) : [])],
    ["within_role_name", (t) => (t.role && t.name
      ? scopes(t.landmarks).flatMap((scope) => qsa("*", scope).filter((el) => roleOf(el) === t.role && nameOf(el) === t.name))
      : [])],
    ["test_id", (t) => (t.test_id
      ? qsa(["data-testid", "data-test-id", "data-test"].map((n) => `[${n}="${CSS.escape(t.test_id)}"]`).join(","))
      : [])],
    ["attributes", (t) => { const selector = attributeSelector(t); return selector ? qsa(selector) : []; }],
    ["text", (t) => (t.text ? ownText(t.text) : [])],
    ["xpath", (t) => (t.xpath ? byXpath(t.xpath) : [])],
    ["css_path", (t) => (t.css_path ? qsa(t.css_path) : [])],
  ];
  const centre = (b) => ({ x: b.x + b.width / 2, y: b.y + b.height / 2 });
  const distance = (el, c) => {
    const here = centre(boundsOf(el));
    return Math.hypot(here.x - c.x, here.y - c.y);
  };
  const nearest = (found, bounds) => {
    if (!bounds || bounds.width === undefined) return found[0];
    const c = centre(bounds);
    return found.slice().sort((a, b) => distance(a, c) - distance(b, c))[0];
  };
  const samePath = (el, marks) => {
    const live = landmarksOf(el);
    return live.length === marks.length && live.every((one, i) => one.role === marks[i].role && one.name === marks[i].name);
  };
  const score = (el, t) => {
    let total = 0;
    const name = nameOf(el);
    if (t.name && name === t.name) total += 3;
    else if (t.name && name && name.includes(t.name)) total += 1;
    for (const key of ["name", "autocomplete", "placeholder"]) {
      if (t.attributes?.[key] && el.getAttribute(key) === t.attributes[key]) total += 1;
    }
    const chain = t.component?.chain || [];
    if (chain.length && chainOf(el).join(" ") === chain.join(" ")) total += 2;
    if (t.bounds?.width !== undefined && distance(el, centre(t.bounds)) <= NEAR_PX) total += 1;
    return total;
  };
  const repair = (t) => {
    if (!t.role) return null;
    const marks = t.landmarks || [];
    const ranked = qsa(CANDIDATES)
      .filter((el) => shown(el) && roleOf(el) === t.role && samePath(el, marks))
      .map((el) => [score(el, t), el])
      .sort((a, b) => b[0] - a[0]);
    const [best, next] = ranked;
    if (!best || best[0] < REPAIR_THRESHOLD) return null;
    if (next && best[0] - next[0] < REPAIR_MARGIN) return null;
    return { el: best[1], score: best[0] };
  };
  const find = (payload) => {
    const t = payload.target || {};
    for (const [strategy, run] of STRATEGIES) {
      const found = run(t, payload).filter(shown);
      if (found.length) return { el: nearest(found, t.bounds), strategy, candidates: found.length, score: null };
    }
    const repairable =
      payload.write === false &&
      REPAIRABLE_ACTIONS.has(payload.action) &&
      !UNREPAIRABLE_ROLES.has(t.role);
    const fixed = repairable ? repair(t) : null;
    return fixed
      ? { el: fixed.el, strategy: "repair", candidates: 1, score: fixed.score }
      : { el: null, strategy: null, candidates: 0, score: null };
  };
  const stateOf = (el) => {
    if (el.isConnected === false) return { value: null, visible: false, enabled: null };
    const secret = (el.type || "").toLowerCase() === "password";
    const setting = settingOf(el);
    return {
      value:
        setting !== undefined ? setting : secret || el.value === undefined || el.value === null ? null : String(el.value),
      visible: shown(el),
      enabled: !(el.disabled === true || el.getAttribute("aria-disabled") === "true"),
    };
  };
  const landed = (asked, got) => {
    if (got === asked) return null;
    return {
      asked: asked.length,
      kept: got.length,
      truncated: got.length < asked.length && asked.startsWith(got),
    };
  };
  const actOn = (el, payload) => {
    let short = null;
    const type = (target, text) => {
      target.focus();
      const proto = target instanceof HTMLTextAreaElement ? HTMLTextAreaElement : HTMLInputElement;
      const setter = Object.getOwnPropertyDescriptor(proto.prototype, "value")?.set;
      const put = (next) => (setter ? setter.call(target, next) : (target.value = next));
      put("");
      target.dispatchEvent(new Event("input", { bubbles: true }));
      for (const character of String(text ?? "")) {
        target.dispatchEvent(new KeyboardEvent("keydown", { key: character, bubbles: true }));
        put(target.value + character);
        target.dispatchEvent(new Event("input", { bubbles: true }));
        target.dispatchEvent(new KeyboardEvent("keyup", { key: character, bubbles: true }));
      }
      target.dispatchEvent(new Event("change", { bubbles: true }));
      short = landed(String(text ?? ""), String(target.value ?? ""));
      target.blur();
      target.dispatchEvent(new FocusEvent("focusout", { bubbles: true }));
      target.dispatchEvent(new FocusEvent("blur"));
    };
    el.scrollIntoView({ block: "center", inline: "center" });
    const problem = (() => {
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
          return "a file cannot be attached from a page script";
        default:
          return `${payload.action} cannot be performed here`;
      }
    })();
    if (problem) {
      return { ok: false, short, error: { kind: "not_actionable", detail: `found the control but ${problem}` } };
    }
    return { ok: true, short };
  };

  const sroPage = {
    perform(payload) {
      const visible = (el) => {
        if (!el || !el.getBoundingClientRect) return false;
        const rect = el.getBoundingClientRect();
        if (rect.width < 1 || rect.height < 1) return false;
        const style = window.getComputedStyle(el);
        return style.visibility !== "hidden" && style.display !== "none";
      };

      const within = (el, scope = payload.within) => {
        if (!scope) return true;
        try {
          const holders = window.Ext?.ComponentQuery?.query(scope) || [];
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
            const all = window.Ext?.ComponentQuery?.query(wanted) || [];
            found = all
              .filter(
                (c) => !locator.visible_only || (c.isVisible && c.isVisible(true)),
              )
              .map((c) => partOf(c, payload.action))
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
        found = found.filter((el) => within(el, locator.within || payload.within));
        if (locator.visible_only) found = found.filter(visible);
        return found;
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

        const done = actOn(found[0], payload);
        if (!done.ok) {
          return { ok: false, error: done.error };
        }
        return {
          ok: true,
          result: {
            performed: true,
            matched_by: locator.strategy,
            candidates: found.length,
            detail: null,
            matched: { strategy: locator.strategy, query: locator.query },
            control: naming(found[0]),
            short: done.short,
          },
        };
      }

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
          if (!wanted.some((one) => said.includes(one) || one.includes(said)))
            continue;
          seen.push({ tag: el.tagName.toLowerCase(), name });
          if (seen.length === 5) break;
        }
        return seen;
      };
      const nearby = nearMisses(payload);
      const also = nearby.length
        ? `; the page has ${nearby.map((one) => `${one.tag} "${one.name}"`).join(", ")}`
        : "";
      return {
        ok: false,
        result: { tried: tried.slice(0, 8) },
        error: {
          kind: "control_not_found",
          detail: `no control matched: ${tried.join(", ") || "nothing"}${also}`,
          nearby,
        },
      };
    },

    performAt(payload) {
      let shortAt = null;
      const el = document.elementFromPoint(payload.x, payload.y);
      if (!el) {
        return {
          ok: false,
          error: { kind: "control_not_found", detail: "nothing at that point" },
        };
      }
      if (el.tagName === "IFRAME" || el.tagName === "FRAME") {
        const box = el.getBoundingClientRect();
        return {
          ok: false,
          error: {
            kind: "point_in_a_frame",
            detail: "that point is inside a frame",
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
          el.blur();
          el.dispatchEvent(new FocusEvent("focusout", { bubbles: true }));
          el.dispatchEvent(new FocusEvent("blur"));
          break;
        }
        case "press": {
          const key = payload.value || "Enter";
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
    },

    screenSize() {
      return {
        url: location.href,
        width: window.innerWidth,
        height: window.innerHeight,
        digest: "",
      };
    },

    viewport() {
      const K_LOOKED_AT = 2000;
      const K_NAMED = 200;
      const width = window.innerWidth;
      const height = window.innerHeight;
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
      } catch {}
      const seen = [];
      const all = document.querySelectorAll(
        "input, select, textarea, button, a, .x-grid-cell, label," +
          " [role=option], [role=menuitem], [role=treeitem], [role=tab], .x-boundlist-item",
      );
      for (const el of document.querySelectorAll(
        "[role=alert], [role=alertdialog], [role=status], [aria-live=assertive], [aria-live=polite]",
      )) {
        const says = (el.innerText || el.textContent || "")
          .trim()
          .replace(/\s+/g, " ");
        if (says) seen.push(`says: ${says.slice(0, 300)}`);
        if (seen.length >= K_NAMED) break;
      }
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
    },

    csrfToken() {
      return window.Ext?.Ajax?.defaultHeaders?.["CSRF-ENCRYPT-TOKEN"] ?? null;
    },

    requestedWith() {
      return (
        window.Ext?.Ajax?.defaultHeaders?.["X-Requested-With"] ?? "XMLHttpRequest"
      );
    },

    async send(payload) {
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
            detail:
              `${error} after ${took}ms` +
              (navigator.onLine === false ? " (this browser is offline)" : ""),
          },
        };
      } finally {
        clearTimeout(giveUp);
      }
    },

    resolve(payload) {
      const f = find(payload);
      return { found: Boolean(f.el), strategy: f.strategy, candidates: f.candidates, score: f.score, xpath: f.el ? xpathOf(f.el) : null };
    },
    act(payload) {
      const f = find(payload);
      if (!f.el) {
        const detail = payload.write === false ? "no strategy and no repair matched" : "no strategy matched, and a write is never repaired";
        return { ok: false, candidates: 0, error: { kind: "control_not_found", detail } };
      }
      let done;
      try {
        done = actOn(f.el, payload);
      } catch (error) {
        done = { ok: false, short: null, error: { kind: "not_actionable", detail: `found the control but ${error.message}` } };
      }
      const repaired = f.strategy === "repair";
      const pin = Math.random().toString(36).slice(2);
      globalThis.__sroActed = { pin, el: f.el, repaired };
      return { ...done, matched_by: f.strategy, candidates: f.candidates, repaired, pin, state: stateOf(f.el) };
    },
    holds(payload) {
      const hit = globalThis.__sroHits?.get(payload.pin);
      const acted = hit ? { el: hit, repaired: false } : globalThis.__sroActed;
      if (!acted || !payload.pin || (!hit && acted.pin !== payload.pin)) return null;
      if (hit) {
        const recorded = find(payload).el;
        if (!recorded || recorded !== hit.closest(CANDIDATES)) return null;
        acted.el = recorded;
      }
      const seen = stateOf(acted.el);
      const want = payload.expect || {};
      const keys = (acted.el.type || "").toLowerCase() === "password" ? ["visible", "enabled"] : ["value", "visible", "enabled"];
      const chosen = acted.el.tagName === "SELECT" && acted.el.isConnected ? [...acted.el.selectedOptions] : [];
      const same = (key) =>
        seen[key] === want[key] || (key === "value" && chosen.some((option) => option.value === want.value));
      const held = keys.every((key) => want[key] === undefined || want[key] === null || same(key));
      return held ? { repaired: acted.repaired } : null;
    },
    hitTest(x, y) {
      let doc = document;
      let el = doc.elementFromPoint(x, y);
      while (el && (el.tagName === "IFRAME" || el.tagName === "FRAME")) {
        const box = el.getBoundingClientRect();
        x -= box.left + (el.clientLeft || 0);
        y -= box.top + (el.clientTop || 0);
        let inner = null;
        try {
          inner = el.contentDocument;
        } catch {
          inner = null;
        }
        if (!inner) {
          const win = doc.defaultView;
          let index = -1;
          for (let i = 0; i < win.frames.length; i += 1) {
            if (win.frames[i] === el.contentWindow) index = i;
          }
          const frame_path = [...framePathOf(win), { index, url: el.src || null }];
          return { strategy: null, query: null, unreachable: "cross_origin_frame", frame_path, x, y };
        }
        doc = inner;
        el = doc.elementFromPoint(x, y);
      }
      if (!el) return null;
      const win = doc.defaultView || window;
      const pin = Math.random().toString(36).slice(2);
      (win.__sroHits ||= new Map()).set(pin, el);
      const frame_path = framePathOf(win);
      const only = (found) => found.length === 1 && found[0] === el;
      const cmp = cmpOf(el);
      if (cmp) {
        const chain = chainOf(el);
        const item = cmp.itemId && !/^ext-/.test(cmp.itemId) ? `#${cmp.itemId}` : null;
        for (const query of [item, chain.slice(-2).join(" "), chain.join(" ")]) {
          if (!query || !(query.startsWith("#") || query.includes(" "))) continue;
          const found = components(query, win);
          if (found.length === 1 && found[0] === cmp) return { strategy: "component", query, frame_path, pin };
        }
      }
      const role = roleOf(el);
      const name = nameOf(el);
      if (role && name && only(qsa("*", doc).filter((one) => roleOf(one) === role && nameOf(one) === name))) {
        return { strategy: "role_and_name", query: `${role}|${name}`, frame_path, pin };
      }
      const testId = el.getAttribute("data-testid");
      if (testId && only(qsa(`[data-testid="${CSS.escape(testId)}"]`, doc))) {
        return { strategy: "test_id", query: testId, frame_path, pin };
      }
      const path = xpathOf(el);
      return only(byXpath(path, doc)) ? { strategy: "xpath", query: path, frame_path, pin } : null;
    },
    signals() {
      const inputs = qsa("input")
        .filter(shown)
        .map((el) => ({
          password: (el.type || "").toLowerCase() === "password",
          tokens: (el.getAttribute("autocomplete") || "").toLowerCase().split(/\s+/).filter(Boolean),
        }));
      return {
        password: inputs.some((one) => one.password && !one.tokens.includes("new-password")),
        autocomplete: [...new Set(inputs.flatMap((one) => one.tokens))],
      };
    },
  };

  globalThis.sroPage = sroPage;
})();
