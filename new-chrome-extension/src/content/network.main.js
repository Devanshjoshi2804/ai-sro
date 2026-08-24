// Patches fetch and XMLHttpRequest in the page's own JS realm.
//
// A content script's default (isolated) world has its own copy of window.fetch
// -- overwriting it there is invisible to the page's own calls. This file is
// registered with world: "MAIN" instead, so the patch is the one the page's
// own code actually calls. It cannot reach chrome.* from here, so a captured
// exchange crosses back to the isolated world as a CustomEvent, which is the
// one channel both worlds share (they share the DOM; they do not share a
// global object).
(() => {
  const MAX_BODY_CHARS = 200000;
  let counter = 0;
  const nextId = () => `req_${Date.now()}_${counter++}`;

  const emit = (record) => {
    window.dispatchEvent(new CustomEvent("sro:request", { detail: JSON.stringify(record) }));
  };

  const isTextual = (contentType) => {
    const ct = (contentType || "").toLowerCase();
    return (
      ct.includes("json") || ct.includes("xml") || ct.includes("text") ||
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

  const truncate = (text) => (text.length > MAX_BODY_CHARS ? text.slice(0, MAX_BODY_CHARS) : text);

  const origFetch = window.fetch;
  if (origFetch) {
    window.fetch = async function sroFetch(input, init) {
      const request_id = nextId();
      const startedAt = new Date();
      const t0 = performance.now();
      const method = (init && init.method) || (input && input.method) || "GET";
      const url = typeof input === "string" ? input : (input && input.url) || String(input);
      let requestHeaders = {};
      try {
        requestHeaders = headersToObject(new Headers((init && init.headers) || (input && input.headers) || {}));
      } catch {
        requestHeaders = {};
      }
      const requestBody = init && init.body;
      const requestBodyText = typeof requestBody === "string" ? truncate(requestBody) : null;

      try {
        const response = await origFetch.call(this, input, init);
        const duration_ms = Math.round(performance.now() - t0);
        const contentType = response.headers.get("content-type");
        let responseBodyText = null;
        if (isTextual(contentType)) {
          try {
            responseBodyText = truncate(await response.clone().text());
          } catch {
            responseBodyText = null;
          }
        }
        emit({
          request_id,
          method,
          url,
          resource_type: "fetch",
          started_at: startedAt.toISOString(),
          request_headers: requestHeaders,
          request_body_text: requestBodyText,
          status: response.status,
          status_text: response.statusText,
          response_headers: headersToObject(response.headers),
          response_body_text: responseBodyText,
          duration_ms,
          redirected: response.redirected,
          final_url: response.url,
          failure_reason: null,
        });
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
          status: null,
          status_text: null,
          response_headers: {},
          response_body_text: null,
          duration_ms: Math.round(performance.now() - t0),
          redirected: false,
          final_url: url,
          failure_reason: String((error && error.message) || error),
        });
        throw error;
      }
    };
  }

  const OrigXHR = window.XMLHttpRequest;
  if (OrigXHR) {
    const OPEN = OrigXHR.prototype.open;
    const SEND = OrigXHR.prototype.send;
    const SET_HEADER = OrigXHR.prototype.setRequestHeader;

    OrigXHR.prototype.open = function sroOpen(method, url, ...rest) {
      this.__sro = { method, url: String(url), headers: {} };
      return OPEN.call(this, method, url, ...rest);
    };
    OrigXHR.prototype.setRequestHeader = function sroSetHeader(name, value) {
      if (this.__sro) this.__sro.headers[name] = value;
      return SET_HEADER.call(this, name, value);
    };
    OrigXHR.prototype.send = function sroSend(body) {
      const state = this.__sro;
      if (state) {
        state.requestBodyText = typeof body === "string" ? truncate(body) : null;
        state.request_id = nextId();
        state.startedAt = new Date();
        state.t0 = performance.now();
        this.addEventListener("loadend", () => {
          const duration_ms = Math.round(performance.now() - state.t0);
          const contentType = this.getResponseHeader("content-type");
          const responseBodyText =
            isTextual(contentType) && typeof this.responseText === "string"
              ? truncate(this.responseText)
              : null;
          const responseHeaders = {};
          (this.getAllResponseHeaders() || "")
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
            status: this.status || null,
            status_text: this.statusText || null,
            response_headers: responseHeaders,
            response_body_text: responseBodyText,
            duration_ms,
            redirected: false,
            final_url: this.responseURL || state.url,
            failure_reason: this.status === 0 ? "network error or aborted" : null,
          });
        });
      }
      return SEND.call(this, body);
    };
  }
})();
