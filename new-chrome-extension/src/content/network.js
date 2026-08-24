// Isolated-world relay for network.main.js's captured exchanges.
//
// The MAIN-world patch cannot reach chrome.runtime; it dispatches a
// CustomEvent instead, the one channel both realms share. Redaction happens
// here rather than there so the credential rules live in the isolated world,
// where the page cannot read or replace them -- sensitivity.generated.js is
// loaded first and puts them on this world's window.
//
// Everything in this file fails closed. A body it cannot inspect is a body it
// cannot promise is clean, so the text is dropped rather than stored: the
// evidence plane keeps what arrives verbatim and there is no second chance to
// redact it later.
(() => {
  const MAX_TEXT = 200000;
  const REDACTED = "«redacted»";

  /** Set when the body could not be inspected, so nothing may be kept from it.
   * Named in `redacted_fields` so a reviewer sees a hole rather than a body
   * that merely happened to contain no credentials. */
  const UNINSPECTABLE = "«whole body: could not be parsed to redact»";

  /** The URL equivalent: stored in place of a URL this world could not check
   * for a credential, rather than the URL itself. */
  const URL_UNINSPECTABLE = "«whole url: could not be checked for a credential»";

  const isSecretName = window.__sroIsSecretName;
  const isSecretHeader = window.__sroIsSecretHeader;
  /** Both come from sensitivity.generated.js. If that file did not run, this
   * one has no idea what a credential looks like, and the safe answer to
   * "is this clean?" is no -- not "nothing matched". */
  const canRedact = typeof isSecretName === "function" && typeof isSecretHeader === "function";

  const contentTypeOf = (headers) => {
    for (const key of Object.keys(headers || {})) {
      if (key.toLowerCase() === "content-type") return headers[key];
    }
    return null;
  };

  const redactJson = (text) => {
    let doc;
    try {
      doc = JSON.parse(text);
    } catch {
      return null; // Not inspectable: caller drops it.
    }
    const removed = [];
    const walk = (node) => {
      if (Array.isArray(node)) return node.map(walk);
      if (node && typeof node === "object") {
        const out = {};
        for (const [key, value] of Object.entries(node)) {
          if (isSecretName(key)) {
            removed.push(key);
            out[key] = REDACTED;
          } else {
            out[key] = walk(value);
          }
        }
        return out;
      }
      return node;
    };
    const cleaned = walk(doc);
    return removed.length ? [JSON.stringify(cleaned), removed] : [text, []];
  };

  const redactForm = (text) => {
    let params;
    try {
      params = new URLSearchParams(text);
    } catch {
      return null;
    }
    const removed = [...new Set([...params.keys()].filter(isSecretName))];
    if (!removed.length) return [text, []];
    for (const key of removed) params.set(key, REDACTED);
    return [params.toString(), removed];
  };

  const XML_FIELD = /<([A-Za-z_][\w.:-]*)([^>]*)>([^<]*)<\/\1>/g;
  const XML_ATTR = /([A-Za-z_][\w.:-]*)\s*=\s*"([^"]*)"/g;

  const redactXml = (text) => {
    const removed = [];
    let cleaned = text.replace(XML_FIELD, (whole, name, attrs) => {
      if (!isSecretName(name.split(":").pop())) return whole;
      removed.push(name);
      return `<${name}${attrs}>${REDACTED}</${name}>`;
    });
    cleaned = cleaned.replace(XML_ATTR, (whole, name) => {
      if (!isSecretName(name.split(":").pop())) return whole;
      removed.push(name);
      return `${name}="${REDACTED}"`;
    });
    return removed.length ? [cleaned, [...new Set(removed)]] : [text, []];
  };

  /** A multipart/form-data body: each part's `Content-Disposition` name and
   * value are on separate lines, so the single-line pair scanner below never
   * sees them together and cannot redact by name at all.
   *
   * `bodyToText` in network.main.js already turns an actual `FormData` object
   * into url-encoded pairs before this file ever sees it -- `redactForm`
   * handles that shape. This exists for the body sent as a pre-built
   * multipart string, which arrives as real multipart wire syntax and reaches
   * here unparsed. */
  const redactMultipart = (text, contentType) => {
    const boundaryMatch = /boundary=(?:"([^"]+)"|([^;]+))/i.exec(contentType || "");
    const boundary = boundaryMatch && (boundaryMatch[1] || boundaryMatch[2]).trim();
    if (!boundary) return redactPairs(text);

    const removed = [];
    const parts = text.split(`--${boundary}`);
    const cleaned = parts
      .map((part) => {
        const headerEnd = part.search(/\r?\n\r?\n/);
        if (headerEnd === -1) return part;
        const header = part.slice(0, headerEnd);
        const nameMatch = /name="([^"]*)"/i.exec(header);
        if (!nameMatch || !isSecretName(nameMatch[1])) return part;
        removed.push(nameMatch[1]);
        const gap = part.slice(headerEnd).match(/^\r?\n\r?\n/)[0];
        const rest = part.slice(headerEnd + gap.length);
        const valueEnd = rest.search(/\r?\n--/);
        return header + gap + REDACTED + rest.slice(valueEnd === -1 ? rest.length : valueEnd);
      })
      .join(`--${boundary}`);
    return removed.length ? [cleaned, [...new Set(removed)]] : [text, []];
  };

  /** Any `name=value` or `name: value` pair, wherever it sits in an otherwise
   * unstructured body. The parsers above each want a whole well-formed
   * document; this wants only a field name next to a field value, which is all
   * a name-based rule needs to act. */
  const PAIR = /([A-Za-z_][\w.-]*)(\s*[=:]\s*)([^\s&;,]*)/g;

  const redactPairs = (text) => {
    const removed = [];
    const cleaned = text.replace(PAIR, (whole, name, separator) => {
      if (!isSecretName(name)) return whole;
      removed.push(name);
      return `${name}${separator}${REDACTED}`;
    });
    return removed.length ? [cleaned, [...new Set(removed)]] : [text, []];
  };

  /** `[text, removedFieldNames]`, or null when the body could not be inspected. */
  const redactBody = (text, contentType) => {
    const kind = (contentType || "").toLowerCase();
    const trimmed = text.trimStart();
    if (kind.includes("json") || trimmed.startsWith("{") || trimmed.startsWith("[")) {
      return redactJson(text);
    }
    if (kind.includes("xml") || trimmed.startsWith("<")) return redactXml(text);
    if (kind.includes("multipart/form-data")) return redactMultipart(text, contentType);
    if (kind.includes("form-urlencoded") || (text.includes("=") && !text.includes("\n"))) {
      return redactForm(text);
    }
    // No parser fits: an unknown content-type, or a `text/plain` post. That is
    // not the same as "no field names are in here" -- `user=alice\npassword=x`
    // matches none of the branches above and used to be stored verbatim with
    // an empty `redacted_fields`, which reads to a reviewer as a body that was
    // checked and found clean. Scanned for pairs instead.
    return redactPairs(text);
  };

  const emptyBody = (contentType, why) => ({
    text: null,
    size_bytes: 0,
    mime_type: (contentType || "").split(";")[0].trim() || null,
    encoding: null,
    redacted_fields: [why],
  });

  const toBody = (text, contentType, truncated) => {
    if (text == null) return null;
    // A prefix of a document is not the document: truncated JSON does not
    // parse, so it cannot be redacted, and storing it unredacted is exactly
    // the failure this whole file exists to prevent.
    if (truncated) return emptyBody(contentType, UNINSPECTABLE);
    if (!canRedact) return emptyBody(contentType, UNINSPECTABLE);

    const result = redactBody(text.slice(0, MAX_TEXT), contentType);
    if (result === null) return emptyBody(contentType, UNINSPECTABLE);

    const [cleaned, redacted] = result;
    return {
      text: cleaned,
      size_bytes: new TextEncoder().encode(cleaned).length,
      mime_type: (contentType || "").split(";")[0].trim() || null,
      encoding: null,
      redacted_fields: redacted,
    };
  };

  /** Headers with every credential value removed and every name kept.
   *
   * An auth, CSRF or session value is never replayed -- `is_replayable` on the
   * Python side answers SEMANTIC only -- so keeping one buys nothing and risks
   * a live session key sitting in the evidence plane for a WMS, a mailbox and
   * every other tab the operator had open. The name stays so the downstream
   * classifier still sees the header was there. */
  const redactHeaders = (headers) => {
    const out = {};
    for (const [name, value] of Object.entries(headers || {})) {
      out[name] = canRedact && isSecretHeader(name) ? REDACTED : value;
    }
    return out;
  };

  /** A URL with credential-named query values removed.
   *
   * The rule itself is generated (sensitivity.generated.js) so the worker and
   * this world cannot disagree about what names a credential. Resolving
   * against `location.href` first is this world's job: a page realm reports
   * whatever it was given, including a relative path. */
  const redactUrl = (url) => {
    // Same rule as the body and header paths above: `canRedact` false means
    // this world never got sensitivity.generated.js's rules, and the safe
    // answer to "is this clean?" is no, not "nothing matched" -- a raw URL
    // returned here is a live token returned here.
    if (!canRedact) return URL_UNINSPECTABLE;
    let resolved;
    try {
      resolved = new URL(url, location.href).toString();
    } catch {
      // Not URL-shaped at all -- nothing a query-string rule could act on,
      // and not a value the redactor would recognise as a URL to check.
      return url;
    }
    return window.__sroRedactUrl(resolved);
  };

  // The other half of network.main.js's handshake. Latches the first secret it
  // is told and then stops listening, so the only value it will ever accept is
  // the one exchanged at document_start -- before any page script existed to
  // send a different one.
  let expected = null;
  const HELLO = "sro:hello";
  const latch = (event) => {
    if (expected !== null) return;
    expected = event.detail;
    window.removeEventListener(HELLO, latch);
  };
  window.addEventListener(HELLO, latch);
  // Covers the page-realm half having loaded first, in which case its opening
  // announcement was made before this listener existed.
  window.dispatchEvent(new CustomEvent("sro:need-hello"));

  const looksLikeRecord = (raw) =>
    raw &&
    typeof raw === "object" &&
    typeof raw.method === "string" &&
    raw.method.length > 0 &&
    typeof raw.url === "string" &&
    raw.url.length > 0 &&
    typeof raw.started_at === "string";

  window.addEventListener("sro:request", (event) => {
    // Any script in the page's realm can dispatch this -- the two realms share
    // no channel a page cannot also write to, so nothing here is trusted on
    // arrival. The shape is checked, the size is capped, and the service worker
    // re-checks the host policy. A page can still forge a plausible exchange;
    // what it cannot do is get an unredacted one, an oversized one, or one for
    // a host the tenant excluded.
    // The cap is the producer's own arithmetic, not a round number:
    // network.main.js allows a request body and a response body of MAX_TEXT
    // each, JSON-escaping roughly doubles a quote-heavy payload, and the
    // headers and envelope ride along too. At MAX_TEXT * 3 an ordinary large
    // API exchange exceeded it and the whole event vanished with no trace --
    // no marker, no error, indistinguishable from a request that never
    // happened. Anything past this cannot have come from our own patch, so
    // dropping it silently is the hostile-page guard it was always meant to be.
    if (typeof event.detail !== "string" || event.detail.length > MAX_TEXT * 8) return;

    let raw;
    try {
      raw = JSON.parse(event.detail);
    } catch {
      return;
    }
    if (!looksLikeRecord(raw)) return;
    // Not from the patch we installed. A page can dispatch this event as
    // easily as we can, and a fabricated exchange would become a candidate
    // skill the operator is one day offered.
    if (expected === null || raw.__from !== expected) return;

    const requestHeaders = raw.request_headers || {};
    const responseHeaders = raw.response_headers || {};

    const request = {
      request_id: raw.request_id,
      method: raw.method,
      url: redactUrl(raw.url),
      resource_type: raw.resource_type,
      started_at: raw.started_at,
      request_headers: redactHeaders(requestHeaders),
      request_body: toBody(
        raw.request_body_text,
        contentTypeOf(requestHeaders),
        Boolean(raw.request_body_truncated),
      ),
      status: raw.status,
      status_text: raw.status_text,
      response_headers: redactHeaders(responseHeaders),
      response_body: toBody(
        raw.response_body_text,
        contentTypeOf(responseHeaders),
        Boolean(raw.response_body_truncated),
      ),
      // Left empty on purpose. The passive tier sees that a redirect happened
      // but not which hops or what they answered, and the protocol's rule for
      // what this tier cannot obtain is that it is omitted, not faked. The
      // teaching tier attaches the debugger and reports the real chain.
      redirect_chain: [],
      duration_ms: raw.duration_ms,
      from_cache: false,
      failure_reason: raw.failure_reason,
      blocked_reason: null,
    };

    chrome.runtime
      .sendMessage({ kind: "request", request, frameUrl: location.href })
      .catch(() => {});
  });
})();
