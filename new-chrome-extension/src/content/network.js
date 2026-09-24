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
  // A frame routinely gets this file more than once. The worker re-injects the
  // isolated half into every watched tab when it starts, and "watch this tab"
  // injects on every press -- and two copies means two listeners on one
  // `sro:request`, so the page realm's single record is forwarded twice. In a
  // day of real recording that was 173 of 367 calls: each duplicate adjacent to
  // its original, byte-identical, same `request_id`, because it was never a
  // second call -- it was the same one relayed again.
  //
  // Not a plain "already installed" flag. After an extension reload the copy in
  // residence is orphaned: its `chrome.runtime` is gone, it can forward nothing,
  // and a flag it had set would keep the live replacement out -- silently
  // recording gestures and no calls, which is the failure the reload fix exists
  // to prevent. Asking whether the copy in residence can still reach the worker
  // answers both cases with one question.
  //
  // observe.js needs no such guard, but only by accident: its top-level `const`
  // throws on a second execution in the same world, so the second copy dies
  // before it can add a listener. This file's IIFE has no such accident, which
  // is the whole of why calls duplicated and gestures did not.
  if (window.__sroRelayingCalls?.()) return;
  window.__sroRelayingCalls = () => Boolean(chrome.runtime?.id);

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
  /** The value rule beside the name rules: a JWT, a PEM block or a bearer
   * scheme is a credential whatever field it arrived in, and a field name is
   * an open vocabulary chosen by whoever wrote the vendor's API. */
  const redactShapes = window.__sroRedactShapes;
  const shapesIn = window.__sroShapesIn;
  /** Spec 5.6. Missing, every page is a sign-in page: its calls keep their
   * method, URL and status and lose their bodies, which is where no rules at
   * all already leaves them. */
  const isSignInDocument = window.__sroIsSignInDocument;
  /** All four come from sensitivity.generated.js. If that file did not run,
   * this one has no idea what a credential looks like, and the safe answer to
   * "is this clean?" is no -- not "nothing matched". */
  const canRedact =
    typeof isSecretName === "function" &&
    typeof isSecretHeader === "function" &&
    typeof redactShapes === "function" &&
    typeof shapesIn === "function";

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

    // The shape pass runs last and over the whole body, whatever parser ran
    // above: it needs no field name, so it reaches a credential in a value the
    // name rule had no name to judge -- and through a body no parser fitted.
    // Named separately in `redacted_fields` because "this went because it
    // looked like a JWT" is a different fact from "this went because it was
    // called password", while the marker left behind is the same either way.
    const [named, redacted] = result;
    const shaped = shapesIn(named);
    const cleaned = shaped.length ? redactShapes(named) : named;
    return {
      text: cleaned,
      size_bytes: new TextEncoder().encode(cleaned).length,
      mime_type: (contentType || "").split(";")[0].trim() || null,
      encoding: null,
      redacted_fields: [...redacted, ...shaped.map((shape) => `«shape: ${shape}»`)],
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
      if (!canRedact) out[name] = value;
      // A header nobody named a credential can still carry one: an
      // `X-Acme-Ticket` holding a JWT is the same secret as an Authorization
      // holding it, and only the value says so.
      else out[name] = isSecretHeader(name) ? REDACTED : redactShapes(value);
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

  // Say so when the exchange never happened, because the alternative is worse
  // than not recording.
  //
  // Reloading the extension replaces this half with a fresh one that knows no
  // realm, while the page-realm half that could tell it is the *old* one, which
  // answered its single hello long ago and stopped listening. The patch is
  // still installed and still emitting; every record it sends is dropped here.
  //
  // It cannot be repaired. The patch lives in the page's own realm, so once
  // page scripts are running there is no channel to it a page cannot also read
  // and write -- the handshake works only because it happens at
  // `document_start`, before any page script exists to overhear it. Answering a
  // hello later hands the secret to whoever asked, and a forged exchange
  // becomes a candidate skill an operator is offered.
  //
  // So the tab reports it instead. Silence here is what cost an operator two
  // demonstrations: gestures recorded, every call dropped, and nothing anywhere
  // saying why.
  setTimeout(() => {
    if (expected !== null) return;
    chrome.runtime
      .sendMessage({
        kind: "calls-not-recordable",
        url: location.href,
        // Whether this page has anything to lose.
        //
        // The fix is a reload and the worker will not do one unasked, for the
        // right reason: a page with a half-filled form on it is exactly the
        // state this system spends its care protecting, and throwing that away
        // to repair its own plumbing would be the worst trade it could make.
        //
        // But a page with nothing typed into it has nothing to lose, and
        // asking somebody to press a button to fix a fault they did not cause
        // -- every time an extension update lands -- is a tax for no benefit.
        // So the page says which it is and the worker decides.
        holding: holdingSomething(),
      })
      .catch(() => {});
  }, 1000);

  /** Whether anything on this page would be lost by reloading it.
   *
   * Deliberately generous about what counts. A false "holding something" costs
   * one banner and one press; a false "holding nothing" costs somebody the
   * form they were half way through, and those are not the same mistake.
   *
   * So: any text a person could have typed, any box they could have ticked
   * away from how it loaded, and any page that has asked the browser to warn
   * before leaving -- which is the page itself saying it has unsaved state,
   * and the only signal here that comes from the application rather than from
   * guessing at its markup.
   */
  function holdingSomething() {
    try {
      for (const field of document.querySelectorAll("input, textarea, select")) {
        if (field.type === "password") return true;
        if (field.type === "checkbox" || field.type === "radio") {
          if (field.checked !== field.defaultChecked) return true;
          continue;
        }
        if (field.tagName === "SELECT") {
          if (field.selectedIndex > 0) return true;
          continue;
        }
        const now = String(field.value ?? "");
        if (now && now !== String(field.defaultValue ?? "")) return true;
      }
      return Boolean(window.onbeforeunload);
    } catch {
      // A page that cannot be read is a page nothing can say this about, and
      // the safe answer to "may I throw this away" is no.
      return true;
    }
  }

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
      // server-capture tier drives the browser over CDP and reports the real
      // chain.
      redirect_chain: [],
      duration_ms: raw.duration_ms,
      from_cache: false,
      failure_reason: raw.failure_reason,
      blocked_reason: null,
    };

    chrome.runtime
      .sendMessage({
        kind: "request",
        request,
        frameUrl: location.href,
        // Spec 5.6: a call made from a page holding a password or one-time-code
        // field keeps its method, URL and status, and the worker drops its
        // bodies.
        signIn: typeof isSignInDocument !== "function" || isSignInDocument(document),
      })
      .catch(() => {});
  });
})();
