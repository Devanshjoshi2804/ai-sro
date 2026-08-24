// Patches fetch and XMLHttpRequest in the page's own JS realm.
//
// A content script's default (isolated) world has its own copy of window.fetch
// -- overwriting it there is invisible to the page's own calls. This file is
// registered with world: "MAIN" instead, so the patch is the one the page's
// own code actually calls. It cannot reach chrome.* from here, so a captured
// exchange crosses back to the isolated world as a CustomEvent, which is the
// one channel both worlds share (they share the DOM; they do not share a
// global object).
//
// Nothing this file does may change what the page observes: same response
// object, same timing, same exceptions. Capture is a side effect or it is a
// bug in somebody else's application.
(() => {
  const MAX_BODY_CHARS = 200000;
  const BODY_READ_TIMEOUT_MS = 10000;

  // Content types whose body is a conversation rather than a document. They
  // stay open for the life of the page, so there is no "the body" to wait for
  // -- reading one to the end is a wait that never returns.
  const NEVER_READ = /event-stream|x-ndjson|multipart\/x-mixed-replace/;

  // Installing twice would wrap our own wrapper and report every exchange once
  // per layer. Marked on the patched functions rather than on `window`: one
  // less global on a page that is not ours.
  const origFetch = window.fetch;
  const OrigXHR = window.XMLHttpRequest;
  if ((origFetch && origFetch.__sro) || (OrigXHR && OrigXHR.prototype.open.__sro)) return;

  // The random half matters: this file runs in every frame of every tab, and a
  // counter plus a millisecond collides across frames that load together.
  const REALM = Math.random().toString(36).slice(2, 10);
  let counter = 0;
  const nextId = () => `req_${REALM}_${counter++}`;

  const emit = (record) => {
    window.dispatchEvent(new CustomEvent("sro:request", { detail: JSON.stringify(record) }));
  };

  const isTextual = (contentType) => {
    const ct = (contentType || "").toLowerCase();
    if (NEVER_READ.test(ct)) return false;
    return (
      ct.includes("json") ||
      ct.includes("xml") ||
      ct.includes("text") ||
      ct.includes("form-urlencoded")
    );
  };

  const headersToObject = (headers) => {
    const out = {};
    if (headers && typeof headers.forEach === "function") {
      headers.forEach((value, key) => {
        out[key] = value;
      });
    }
    return out;
  };

  /** A request payload as text, for the shapes a page actually sends.
   *
   * A form POST built from URLSearchParams or FormData is the common case in
   * every app this will ever watch, and reporting those as "no body" would
   * lose exactly the values a skill needs as parameters. Binary payloads stay
   * unread: they are not text and guessing an encoding here would be a lie
   * about what was sent. */
  const bodyToText = (body) => {
    if (body == null) return null;
    if (typeof body === "string") return body;
    try {
      if (typeof URLSearchParams !== "undefined" && body instanceof URLSearchParams) {
        return body.toString();
      }
      if (typeof FormData !== "undefined" && body instanceof FormData) {
        const pairs = new URLSearchParams();
        for (const [key, value] of body.entries()) {
          // A file's contents are not evidence of what was done; its name is.
          pairs.append(key, typeof value === "string" ? value : `«file:${value.name || "blob"}»`);
        }
        return pairs.toString();
      }
    } catch {
      return null;
    }
    return null;
  };

  /**
   * Our own copy of a response body, bounded in both size and time.
   *
   * Bounded in time because a body can be a stream that never ends, and
   * bounded in size because `.text()` on a large download would hold the whole
   * thing in memory twice. Says when it stopped early: a prefix of a JSON
   * document cannot be parsed, so it cannot be redacted, and the isolated
   * world needs to know that rather than guess it.
   */
  const readBody = async (response, contentType) => {
    if (!isTextual(contentType)) return { text: null, truncated: false };
    if (!response.body) {
      try {
        const whole = await response.text();
        return { text: whole.slice(0, MAX_BODY_CHARS), truncated: whole.length > MAX_BODY_CHARS };
      } catch {
        return { text: null, truncated: false };
      }
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let out = "";
    let stoppedEarly = false;
    const giveUp = setTimeout(() => {
      stoppedEarly = true;
      reader.cancel().catch(() => {});
    }, BODY_READ_TIMEOUT_MS);

    try {
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        out += decoder.decode(value, { stream: true });
        if (out.length >= MAX_BODY_CHARS) {
          stoppedEarly = true;
          break;
        }
      }
    } catch {
      stoppedEarly = true;
    } finally {
      clearTimeout(giveUp);
      reader.cancel().catch(() => {});
    }

    return { text: out ? out.slice(0, MAX_BODY_CHARS) : null, truncated: stoppedEarly };
  };

  if (origFetch) {
    const patched = async function sroFetch(input, init) {
      const request_id = nextId();
      const startedAt = new Date();
      const t0 = performance.now();
      const method = (init && init.method) || (input && input.method) || "GET";
      const url = typeof input === "string" ? input : (input && input.url) || String(input);
      let requestHeaders = {};
      try {
        requestHeaders = headersToObject(
          new Headers((init && init.headers) || (input && input.headers) || {}),
        );
      } catch {
        requestHeaders = {};
      }
      // ponytail: a body carried on a Request object rather than in `init` is
      // not read -- doing so needs input.clone() and an await before the call
      // goes out. Add if a real app is seen to send one.
      const requestBodyText = bodyToText(init && init.body);

      try {
        const response = await origFetch.call(this, input, init);
        const duration_ms = Math.round(performance.now() - t0);
        const contentType = response.headers.get("content-type");
        const responseHeaders = headersToObject(response.headers);
        const redirected = response.redirected;
        const finalUrl = response.url;
        const status = response.status;
        const statusText = response.statusText;

        // The page gets its response now, before we have read anything. A body
        // that never ends would otherwise be a fetch that never resolves, and
        // an extension that hangs the application it is watching is worse than
        // one that captures nothing.
        readBody(response.clone(), contentType)
          .then(({ text, truncated }) => {
            emit({
              request_id,
              method,
              url,
              resource_type: "fetch",
              started_at: startedAt.toISOString(),
              request_headers: requestHeaders,
              request_body_text: requestBodyText,
              request_body_truncated: false,
              status,
              status_text: statusText,
              response_headers: responseHeaders,
              response_body_text: text,
              response_body_truncated: truncated,
              duration_ms,
              redirected,
              final_url: finalUrl,
              failure_reason: null,
            });
          })
          .catch(() => {});

        return response;
      } catch (error) {
        emit({
          request_id,
          method,
          url,
          resource_type: "fetch",
          started_at: startedAt.toISOString(),
          request_headers: requestHeaders,
          request_body_text: requestBodyText,
          request_body_truncated: false,
          status: null,
          status_text: null,
          response_headers: {},
          response_body_text: null,
          response_body_truncated: false,
          duration_ms: Math.round(performance.now() - t0),
          redirected: false,
          final_url: url,
          failure_reason: String((error && error.message) || error),
        });
        throw error;
      }
    };
    patched.__sro = true;
    window.fetch = patched;
  }

  if (OrigXHR) {
    const OPEN = OrigXHR.prototype.open;
    const SEND = OrigXHR.prototype.send;
    const SET_HEADER = OrigXHR.prototype.setRequestHeader;

    const open = function sroOpen(method, url, ...rest) {
      this.__sro = { method, url: String(url), headers: {} };
      // Bound once per object, never once per send. An XHR may legally be
      // reopened and reused; a listener added in `send` stayed attached with
      // the *previous* call's state closed over it, so the second response was
      // reported twice -- once correctly, and once pairing the first call's
      // method, url and body with the second call's status and response.
      if (!this.__sroBound) {
        this.__sroBound = true;
        this.addEventListener("loadend", () => report(this));
      }
      return OPEN.call(this, method, url, ...rest);
    };
    open.__sro = true;
    OrigXHR.prototype.open = open;

    OrigXHR.prototype.setRequestHeader = function sroSetHeader(name, value) {
      if (this.__sro) this.__sro.headers[name] = value;
      return SET_HEADER.call(this, name, value);
    };

    /** Reads whatever the *current* `open`/`send` pair produced. */
    const report = (xhr) => {
      const state = xhr.__sro;
      if (!state || state.startedAt === undefined) return;

      const duration_ms = Math.round(performance.now() - state.t0);
      const contentType = xhr.getResponseHeader("content-type");

      // `responseText` is not a plain property: reading it throws unless
      // responseType is "" or "text", and `typeof` does not guard a getter
      // that throws. responseType "json" is the common case in every app
      // written this decade, and it was losing every one of those calls --
      // silently, plus an uncaught exception in the page's console each time.
      let raw = null;
      try {
        const kind = xhr.responseType;
        if (kind === "" || kind === "text") raw = xhr.responseText;
        else if (kind === "json" && xhr.response != null) raw = JSON.stringify(xhr.response);
      } catch {
        raw = null;
      }
      const readable = isTextual(contentType) && typeof raw === "string";
      const responseBodyText = readable ? raw.slice(0, MAX_BODY_CHARS) : null;
      const truncated = readable && raw.length > MAX_BODY_CHARS;

      const responseHeaders = {};
      (xhr.getAllResponseHeaders() || "")
        .trim()
        .split(/\r?\n/)
        .filter(Boolean)
        .forEach((line) => {
          const idx = line.indexOf(":");
          if (idx > 0) responseHeaders[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
        });

      emit({
        request_id: state.request_id,
        method: state.method,
        url: state.url,
        resource_type: "xhr",
        started_at: state.startedAt.toISOString(),
        request_headers: state.headers,
        request_body_text: state.requestBodyText,
        request_body_truncated: false,
        status: xhr.status || null,
        status_text: xhr.statusText || null,
        response_headers: responseHeaders,
        response_body_text: responseBodyText,
        response_body_truncated: truncated,
        duration_ms,
        redirected: false,
        final_url: xhr.responseURL || state.url,
        failure_reason: xhr.status === 0 ? "network error or aborted" : null,
      });
    };

    OrigXHR.prototype.send = function sroSend(body) {
      const state = this.__sro;
      if (state) {
        state.requestBodyText = bodyToText(body);
        state.request_id = nextId();
        state.startedAt = new Date();
        state.t0 = performance.now();
      }
      return SEND.call(this, body);
    };
  }
})();
