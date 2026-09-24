(() => {
  const REPAIR_THRESHOLD = 6;
  const NEAR_PX = 50;
  const GENERATED_ID = /^(ext-|gen)|\d{3,}/;
  const CANDIDATES = "input, select, textarea, button, a, [role], [tabindex]";
  const LANDMARKS = ["region", "dialog", "alertdialog", "grid", "treegrid", "form"];

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
  const nameOf = (el) => {
    const aria = el.getAttribute("aria-label");
    if (aria) return aria.trim();
    const by = el.getAttribute("aria-labelledby");
    if (by) return by.split(/\s+/).map((id) => document.getElementById(id)?.innerText || "").join(" ").trim();
    if (el.labels && el.labels.length) return (el.labels[0].innerText || "").trim();
    return (el.getAttribute("placeholder") || el.getAttribute("title") || el.innerText || "").trim().slice(0, 200);
  };
  const landmarkRole = (el) => {
    const written = el.getAttribute("role");
    if (written) return LANDMARKS.includes(written) ? written : null;
    const tag = el.tagName.toLowerCase();
    return tag === "form" ? "form" : tag === "dialog" ? "dialog" : tag === "section" ? "region" : null;
  };
  const landmarksOf = (el) => {
    const found = [];
    for (let node = el.parentElement; node; node = node.parentElement) {
      const role = landmarkRole(node);
      const name = role ? node.getAttribute("aria-label") || null : null;
      if (role && name) found.unshift({ role, name });
    }
    return found;
  };
  const ext = (query) =>
    (window.Ext?.ComponentQuery?.query(query) || [])
      .filter((c) => c.isVisible?.(true))
      .map((c) => (c.inputEl || c.btnEl || c.el)?.dom)
      .filter(Boolean);
  const chainOf = (el) => {
    if (!window.Ext?.getCmp) return [];
    let node = el;
    let cmp = null;
    while (node && node.nodeType === 1 && !cmp) {
      if (node.id) {
        cmp = window.Ext.getCmp(node.id) || window.Ext.getCmp(node.id.replace(/-[a-zA-Z]+El$/, ""));
      }
      node = node.parentElement;
    }
    if (!cmp) return [];
    const chain = [];
    for (let k = cmp; k && chain.length < 10; k = k.ownerCt || k.floatParent) {
      const xtype = k.getXType ? k.getXType() : k.xtype;
      if (!xtype) continue;
      chain.unshift(k.itemId && !/^ext-/.test(k.itemId) ? `${xtype}#${k.itemId}` : xtype);
    }
    return chain;
  };
  const ownText = (text) =>
    qsa("button, a, label, td, th, li, span, div, option").filter(
      (el) => [...el.childNodes].filter((n) => n.nodeType === 3).map((n) => n.textContent).join("").trim() === text,
    );
  const scopes = (landmarks) => {
    const inner = (landmarks || []).at(-1);
    if (!inner) return [document];
    return qsa("*").filter((el) => landmarkRole(el) === inner.role && nameOf(el) === inner.name);
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
  const byXpath = (xpath) => {
    try {
      const got = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
      return Array.from({ length: got.snapshotLength }, (_, i) => got.snapshotItem(i));
    } catch {
      return [];
    }
  };
  const byLearned = ({ strategy, query }) => {
    if (strategy === "component") return ext(query.startsWith("#") || query.includes(" ") ? query : `#${query}`);
    if (strategy === "role_and_name") {
      const [role, name] = query.split("|");
      return qsa("*").filter((el) => roleOf(el) === role && nameOf(el) === name);
    }
    if (strategy === "test_id") return qsa(`[data-testid="${CSS.escape(query)}"]`);
    if (strategy === "text") return ownText(query);
    if (strategy === "xpath") return byXpath(query);
    return qsa(query);
  };
  const STRATEGIES = [
    ["learned", (t, p) => (p.learned ? byLearned(p.learned) : [])],
    ["component_chain", (t) => (t.component?.chain?.length > 1 ? ext(t.component.chain.join(" ")) : [])],
    ["component", (t) => (t.component?.query ? ext(t.component.query) : t.component?.item_id ? ext(`#${t.component.item_id}`) : [])],
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
    const here = centre(el.getBoundingClientRect());
    return Math.hypot(here.x - c.x, here.y - c.y);
  };
  const nearest = (found, bounds) => {
    if (!bounds || bounds.width === undefined) return found[0];
    const c = centre(bounds);
    return found.slice().sort((a, b) => distance(a, c) - distance(b, c))[0];
  };
  const score = (el, t) => {
    let total = 0;
    if (t.role && roleOf(el) === t.role) total += 3;
    const name = nameOf(el);
    if (t.name && name === t.name) total += 3;
    else if (t.name && name && name.includes(t.name)) total += 1;
    for (const key of ["name", "autocomplete", "type", "placeholder"]) {
      if (t.attributes?.[key] && el.getAttribute(key) === t.attributes[key]) total += 1;
    }
    const chain = t.component?.chain || [];
    if (chain.length && chainOf(el).join(" ") === chain.join(" ")) total += 2;
    const marks = t.landmarks || [];
    if (marks.length && JSON.stringify(landmarksOf(el)) === JSON.stringify(marks)) total += 2;
    if (t.bounds?.width !== undefined && distance(el, centre(t.bounds)) <= NEAR_PX) total += 1;
    return total;
  };
  const repair = (t) => {
    const ranked = qsa(CANDIDATES).filter(shown).map((el) => [score(el, t), el]).sort((a, b) => b[0] - a[0]);
    const [best, next] = ranked;
    if (!best || best[0] < REPAIR_THRESHOLD || (next && next[0] === best[0])) return null;
    return { el: best[1], score: best[0] };
  };
  const find = (payload) => {
    const t = payload.target || {};
    for (const [strategy, run] of STRATEGIES) {
      const found = run(t, payload).filter(shown);
      if (found.length) return { el: nearest(found, t.bounds), strategy, candidates: found.length, score: null };
    }
    const fixed = repair(t);
    return fixed
      ? { el: fixed.el, strategy: "repair", candidates: 1, score: fixed.score }
      : { el: null, strategy: null, candidates: 0, score: null };
  };
  const stateOf = (el) => {
    const secret = (el.type || "").toLowerCase() === "password";
    return {
      value: secret || el.value === undefined || el.value === null ? null : String(el.value),
      visible: shown(el),
      enabled: !(el.disabled === true || el.getAttribute("aria-disabled") === "true"),
    };
  };
  const xpathOf = (el) => {
    const parts = [];
    let node = el;
    while (node && node.nodeType === 1 && parts.length < 12) {
      const parent = node.parentElement;
      if (!parent) {
        parts.unshift(node.tagName.toLowerCase());
        break;
      }
      const siblings = [...parent.children].filter((c) => c.tagName === node.tagName);
      const index = siblings.indexOf(node) + 1;
      parts.unshift(`${node.tagName.toLowerCase()}[${index}]`);
      node = parent;
    }
    return `/${parts.join("/")}`;
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

      const partOf = (c) => {
        if (payload.action === "click") {
          const arrow = triggerOf(c);
          if (arrow) return arrow;
        }
        return (c.inputEl || c.btnEl || c.el)?.dom;
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
              .map((c) => partOf(c))
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
      if (!f.el) return { ok: false, candidates: 0, error: { kind: "control_not_found", detail: "no strategy and no repair matched" } };
      const done = actOn(f.el, payload);
      return { ...done, matched_by: f.strategy, candidates: f.candidates, state: stateOf(f.el) };
    },
    holds(payload) {
      const f = find(payload);
      if (!f.el) return false;
      const seen = stateOf(f.el);
      const want = payload.expect || {};
      return ["value", "visible", "enabled"].every((key) => want[key] === undefined || want[key] === null || seen[key] === want[key]);
    },
    hitTest(x, y) {
      let el = document.elementFromPoint(x, y);
      let doc = document;
      while (el && el.tagName === "IFRAME" && el.contentDocument) {
        const box = el.getBoundingClientRect();
        doc = el.contentDocument;
        el = doc.elementFromPoint(x - box.left, y - box.top);
      }
      if (!el) return null;
      const only = (found) => found.length === 1 && found[0] === el;
      const item = window.Ext?.getCmp?.(el.id)?.itemId;
      if (item && only(ext(`#${item}`))) return { strategy: "component", query: `#${item}` };
      const role = roleOf(el), name = nameOf(el);
      if (role && name && only(qsa("*", doc).filter((one) => roleOf(one) === role && nameOf(one) === name))) {
        return { strategy: "role_and_name", query: `${role}|${name}` };
      }
      const testId = el.getAttribute("data-testid");
      if (testId) return { strategy: "test_id", query: testId };
      return { strategy: "xpath", query: xpathOf(el) };
    },
  };

  globalThis.sroPage = sroPage;
})();
