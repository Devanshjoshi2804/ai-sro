// Isolated-world relay for network.main.js's captured exchanges.
//
// The MAIN-world patch cannot reach chrome.runtime; it dispatches a
// CustomEvent instead, the one channel both worlds share. Redaction happens
// here rather than in MAIN world so the credential word list stays one
// generated file (recorder.generated.js, already loaded first) instead of a
// second copy baked into the page-world patch.
(() => {
  const MAX_TEXT = 200000;

  const isSecretName = (name) => (window.__sroIsSecretName ? window.__sroIsSecretName(name) : false);

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
      return [text, []];
    }
    const removed = [];
    const walk = (node) => {
      if (Array.isArray(node)) return node.map(walk);
      if (node && typeof node === "object") {
        const out = {};
        for (const [key, value] of Object.entries(node)) {
          if (isSecretName(key)) {
            removed.push(key);
            out[key] = "«redacted»";
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
      return [text, []];
    }
    const removed = [...new Set([...params.keys()].filter(isSecretName))];
    if (!removed.length) return [text, []];
    for (const key of removed) params.set(key, "«redacted»");
    return [params.toString(), removed];
  };

  const XML_FIELD = /<([A-Za-z_][\w.:-]*)([^>]*)>([^<]*)<\/\1>/g;
  const XML_ATTR = /([A-Za-z_][\w.:-]*)\s*=\s*"([^"]*)"/g;

  const redactXml = (text) => {
    const removed = [];
    let cleaned = text.replace(XML_FIELD, (whole, name, attrs) => {
      if (!isSecretName(name.split(":").pop())) return whole;
      removed.push(name);
      return `<${name}${attrs}>«redacted»</${name}>`;
    });
    cleaned = cleaned.replace(XML_ATTR, (whole, name) => {
      if (!isSecretName(name.split(":").pop())) return whole;
      removed.push(name);
      return `${name}="«redacted»"`;
    });
    return removed.length ? [cleaned, [...new Set(removed)]] : [text, []];
  };

  const redactBody = (text, contentType) => {
    const kind = (contentType || "").toLowerCase();
    const trimmed = text.trimStart();
    if (kind.includes("json") || trimmed.startsWith("{") || trimmed.startsWith("[")) return redactJson(text);
    if (kind.includes("xml") || trimmed.startsWith("<")) return redactXml(text);
    if (kind.includes("form-urlencoded") || (text.includes("=") && !text.includes("\n"))) return redactForm(text);
    return [text, []];
  };

  const toBody = (text, contentType) => {
    if (text == null) return null;
    const truncated = text.length > MAX_TEXT ? text.slice(0, MAX_TEXT) : text;
    const [cleaned, redacted] = redactBody(truncated, contentType);
    return {
      text: cleaned,
      size_bytes: new TextEncoder().encode(cleaned).length,
      mime_type: (contentType || "").split(";")[0].trim() || null,
      encoding: null,
      redacted_fields: redacted,
    };
  };

  window.addEventListener("sro:request", (event) => {
    let raw;
    try {
      raw = JSON.parse(event.detail);
    } catch {
      return;
    }
    const request = {
      request_id: raw.request_id,
      method: raw.method,
      url: raw.url,
      resource_type: raw.resource_type,
      started_at: raw.started_at,
      request_headers: raw.request_headers || {},
      request_body: toBody(raw.request_body_text, contentTypeOf(raw.request_headers)),
      status: raw.status,
      status_text: raw.status_text,
      response_headers: raw.response_headers || {},
      response_body: toBody(raw.response_body_text, contentTypeOf(raw.response_headers)),
      redirect_chain:
        raw.redirected && raw.final_url && raw.final_url !== raw.url
          ? [{ url: raw.url, status: raw.status || 0, location: raw.final_url }]
          : [],
      duration_ms: raw.duration_ms,
      from_cache: false,
      failure_reason: raw.failure_reason,
      blocked_reason: null,
    };
    chrome.runtime.sendMessage({ kind: "request", request, frameUrl: location.href }).catch(() => {});
  });
})();
