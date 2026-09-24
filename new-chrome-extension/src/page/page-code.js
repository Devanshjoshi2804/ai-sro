(() => {
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

      let short = null;

      const landed = (asked, got) => {
        if (got === asked) return null;
        return {
          asked: asked.length,
          kept: got.length,
          truncated: got.length < asked.length && asked.startsWith(got),
        };
      };

      const type = (el, text) => {
        el.focus();
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
        short = landed(String(text ?? ""), String(el.value ?? ""));
        el.blur();
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
            matched: { strategy: locator.strategy, query: locator.query },
            control: naming(found[0]),
            short,
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
  };

  try {
    Object.defineProperty(globalThis, "sroPage", { value: sroPage, writable: false, configurable: false });
  } catch {}
})();
