// Injected into every frame before page scripts run.
//
// CDP reports what the *page* did; it does not report what the *human* did when
// they are driving the session themselves through the live view. This listener
// is the only source of input events, and each one it emits opens an action
// frame server-side.
//
// Contract: calls window.__sroRecord(json) exactly once per meaningful gesture.
// Roles and accessible names are filled in server-side from the AX tree taken at
// the same instant; what this collects is the DOM detail the AX tree cannot give.

(() => {
  // Installation is idempotent by construction rather than by a flag.
  //
  // `document.open()` -- how a page replaces its content without navigating --
  // unregisters every listener on the window while keeping both the window and
  // the document object identity, so a boolean guard on either one reports the
  // recorder as installed after its listeners have been wiped, and capture goes
  // quiet for the rest of the session. Rather than guess which object survives
  // which teardown, keep the handlers and remove them before adding them: a
  // removeEventListener for a listener that is already gone is a no-op.
  const INSTALLED = "__sroHandlers";
  for (const [type, handler] of window[INSTALLED] || []) {
    window.removeEventListener(type, handler, true);
  }
  const handlers = [];
  window[INSTALLED] = handlers;

  const listen = (type, handler) => {
    handlers.push([type, handler]);
    window.addEventListener(type, handler, true);
  };

  const MAX_TEXT = 200;

  // A credential field is recognised where it is typed, not later. Anything
  // matched here has its value dropped before it leaves the page: the evidence
  // plane keeps everything a demonstration did, and a password is not that --
  // it is a key to the customer's system.
  // Whole words, not substrings. Matched loosely this ate ordinary business
  // data -- an address search box came back as «secret», so the demonstration
  // could not say what was searched for, the model narrating it described a
  // hole, and the value that would have become a parameter was gone. A
  // redaction that eats business data is how people learn to switch it off.
  // Substituted from sensitivity.SECRET_TOKENS when this file is injected --
  // there is one list, on the Python side, and this used to be a second copy of
  // it that drifted. Injection fails loudly rather than shipping the marker.
  const SECRET_WORDS = new Set(__SECRET_WORDS__);
  const wordsOf = (text) =>
    (text || '')
      .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
      .split(/[^A-Za-z]+/)
      .filter(Boolean)
      .map((word) => word.toLowerCase());
  const isSecretField = (el) => {
    if (!el || el.nodeType !== 1) return false;
    // What the page itself says is a credential, which is the only signal here
    // that is a decision rather than a guess.
    if ((el.type || '').toLowerCase() === 'password') return true;
    const autocomplete = (el.getAttribute('autocomplete') || '').toLowerCase();
    if (autocomplete.includes('password') || autocomplete === 'one-time-code') return true;
    if (autocomplete === 'cc-csc' || autocomplete === 'cc-number') return true;
    const named = [el.name, el.id, el.getAttribute('aria-label'), el.getAttribute('placeholder')]
      .filter(Boolean)
      .join(' ');
    const words = wordsOf(named);
    return words.some((word) => SECRET_WORDS.has(word)) || SECRET_WORDS.has(words.join(''));
  };

  const cssPath = (el) => {
    const parts = [];
    let node = el;
    while (node && node.nodeType === 1 && parts.length < 8) {
      let part = node.tagName.toLowerCase();
      if (node.id) {
        parts.unshift(`${part}#${CSS.escape(node.id)}`);
        break;
      }
      const cls = (node.className || '').toString().trim().split(/\s+/).filter(Boolean)[0];
      if (cls) part += `.${CSS.escape(cls)}`;
      const parent = node.parentElement;
      if (parent) {
        const siblings = [...parent.children].filter((c) => c.tagName === node.tagName);
        if (siblings.length > 1) part += `:nth-of-type(${siblings.indexOf(node) + 1})`;
      }
      parts.unshift(part);
      node = node.parentElement;
    }
    return parts.join(' > ');
  };

  const xpath = (el) => {
    const parts = [];
    let node = el;
    while (node && node.nodeType === 1 && parts.length < 12) {
      const parent = node.parentElement;
      if (!parent) { parts.unshift(node.tagName.toLowerCase()); break; }
      const siblings = [...parent.children].filter((c) => c.tagName === node.tagName);
      const index = siblings.indexOf(node) + 1;
      parts.unshift(`${node.tagName.toLowerCase()}[${index}]`);
      node = parent;
    }
    return `/${parts.join('/')}`;
  };

  // Best-effort label. The authoritative accessible name comes from the AX tree.
  const label = (el) => {
    // Never for a credential field: the last fallback below is `el.value`, so a
    // password with no label would become its own accessible name.
    if (isSecretField(el)) return null;
    const aria = el.getAttribute('aria-label');
    if (aria) return aria;
    const labelledBy = el.getAttribute('aria-labelledby');
    if (labelledBy) {
      const target = document.getElementById(labelledBy);
      if (target) return (target.innerText || '').trim().slice(0, MAX_TEXT);
    }
    if (el.labels && el.labels.length) return (el.labels[0].innerText || '').trim().slice(0, MAX_TEXT);
    if (el.getAttribute('placeholder')) return el.getAttribute('placeholder');
    if (el.getAttribute('title')) return el.getAttribute('title');
    return (el.innerText || el.value || '').trim().slice(0, MAX_TEXT) || null;
  };

  // The component behind the element, when the page is built out of components.
  //
  // ExtJS renders every control as nested `<div>`s with ids like `ext-gen4443`
  // that are assigned in render order, so a selector recorded today matches a
  // different control tomorrow -- and the accessibility tree, measured on four
  // screens of this WMS, carries no role for most of them and never carries the
  // payload key. The component model is the only view that survives a reload:
  // `xtype` is what the application calls the control, and `itemId` is what its
  // own code uses to find it.
  const component = (el) => {
    if (!window.Ext || !Ext.getCmp) return null;
    let node = el;
    let cmp = null;
    while (node && node.nodeType === 1 && !cmp) {
      if (node.id) {
        // Ext gives sub-elements suffixed ids (`-inputEl`, `-btnIconEl`); the
        // component is registered under the stem.
        cmp = Ext.getCmp(node.id) || Ext.getCmp(node.id.replace(/-[a-zA-Z]+El$/, ''));
      }
      node = node.parentElement;
    }
    if (!cmp) return null;

    const chain = [];
    for (let k = cmp; k && chain.length < 10; k = k.ownerCt || k.floatParent) {
      const xtype = k.getXType ? k.getXType() : k.xtype;
      if (!xtype) continue;
      chain.unshift(k.itemId && !/^ext-/.test(k.itemId) ? `${xtype}#${k.itemId}` : xtype);
    }
    // Two segments: enough context to disambiguate, short enough to survive a
    // screen being re-parented, which happens whenever a dialog is involved.
    const query = chain.slice(-2).join(' ');
    return {
      framework: 'extjs',
      xtype: cmp.getXType ? cmp.getXType() : cmp.xtype,
      itemId: cmp.itemId && !/^ext-/.test(cmp.itemId) ? cmp.itemId : null,
      name: cmp.name || null,
      fieldLabel: cmp.fieldLabel || null,
      text: typeof cmp.text === 'string' ? cmp.text.slice(0, MAX_TEXT) : null,
      query,
      chain,
    };
  };

  const describe = (el) => {
    if (!el || el.nodeType !== 1) return null;
    const secret = isSecretField(el);
    const box = el.getBoundingClientRect();
    const attributes = {};
    for (const attr of el.attributes || []) {
      // Values are captured; nothing here is filtered. Storage-side policy
      // decides what may leave the evidence plane.
      // `value` on a credential field is the credential itself: omit the
      // attribute rather than blanking it, so nothing downstream stringifies a
      // placeholder into the recording.
      if (attr.name === 'value' && secret) continue;
      attributes[attr.name] = String(attr.value).slice(0, 512);
    }
    return {
      tag: el.tagName.toLowerCase(),
      role: el.getAttribute('role') || null,
      name: label(el),
      secret,
      text: secret ? null : (el.innerText || '').trim().slice(0, MAX_TEXT) || null,
      testId:
        el.getAttribute('data-testid') ||
        el.getAttribute('data-test-id') ||
        el.getAttribute('data-test') ||
        null,
      cssPath: cssPath(el),
      xpath: xpath(el),
      bounds: { x: box.x, y: box.y, width: box.width, height: box.height },
      attributes,
      component: component(el),
    };
  };

  const modifiers = (e) => {
    const mods = [];
    if (e.ctrlKey) mods.push('ctrl');
    if (e.shiftKey) mods.push('shift');
    if (e.altKey) mods.push('alt');
    if (e.metaKey) mods.push('meta');
    return mods;
  };

  const emit = (record) => {
    try {
      window.__sroRecord(JSON.stringify({ ...record, at: Date.now() / 1000, url: location.href }));
    } catch {
      // The binding is not installed yet, or the frame is being torn down.
      // Losing a gesture is preferable to breaking the page the operator is using.
    }
  };

  listen('click', (e) =>
    emit({ kind: 'click', target: describe(e.target), modifiers: modifiers(e) }),
  );

  // One event per completed edit rather than per keystroke: `change` fires on
  // blur, so the value recorded is what the human settled on.
  listen('change', (e) => {
    const el = e.target;
    if (!el) return;
    if (el.type === 'file' && el.files) {
      emit({
        kind: 'upload',
        target: describe(el),
        value: [...el.files].map((file) => file.name).join(', '),
        modifiers: [],
      });
      return;
    }
    const kind = el.tagName === 'SELECT' ? 'select' : 'type';
    const secret = isSecretField(el);
    emit({
      kind,
      target: describe(el),
      value: secret ? null : (el.value ?? null),
      secret,
      modifiers: [],
    });
  });

  listen('keydown', (e) => {
    // Only keys that commit or cancel. Every other keystroke arrives as the
    // `change` value above.
    if (!['Enter', 'Escape', 'Tab'].includes(e.key)) return;
    emit({ kind: 'press', target: describe(e.target), value: e.key, modifiers: modifiers(e) });
  });

  let scrollTimer = null;
  listen('scroll', () => {
    // Debounced: a scroll is one gesture, not four hundred events.
    if (scrollTimer) clearTimeout(scrollTimer);
    scrollTimer = setTimeout(
      () => emit({ kind: 'scroll', value: String(Math.round(window.scrollY)), modifiers: [] }),
      400,
    );
  });
})();
