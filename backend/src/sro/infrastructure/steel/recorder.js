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
  // What the operator actually typed, which is the thing that becomes a
  // parameter, so it gets far more room than a label does -- but not unbounded
  // room. observe.js drops a gesture whose JSON is over 128 KB, so an uncapped
  // `value` from a notes field or a pasted spreadsheet took the whole gesture
  // with it: the mined episode then showed a save with no edit before it.
  // Losing the tail of one field beats losing the fact that it was edited.
  const MAX_VALUE = 4096;

  // How a control is named, placed, scoped and pathed. Spliced in from
  // page-code.js's `readers` by `_recorder_script` (capture.py): what this
  // records and what page-code.js later resolves it against are one text, so
  // the two cannot disagree about a control. Reasoning lives in
  // docs/code-notes/new-chrome-extension/src/page/page-code.js.md.
  const {
    roleOf, nameOf, landmarksOf, cmpOf, chainOf, xpathOf, boundsOf, framePathOf, settingOf, requiredOf, outlineOf,
    isSecretField, labelOf, fullNameOf, siblingOf, choiceOf, placeOf, watchEffect,
  } = __PAGE_READERS__;

  const stateOf = (el) => {
    if (!el || el.nodeType !== 1 || el.isConnected === false) {
      return { value: null, visible: false, enabled: null };
    }
    const box = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    const visible =
      box.width > 0 && box.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
    const enabled = !(el.disabled === true || el.getAttribute('aria-disabled') === 'true');
    const setting = isSecretField(el) ? null : settingOf(el);
    return { value: setting ? setting.slice(0, MAX_VALUE) : null, visible, enabled };
  };

  const REALM = Math.random().toString(36).slice(2);
  let count = 0;
  let last = null;
  let lastRef = null;
  let watching = null;
  const sendEffect = (of, of_at) => (effect) => {
    try {
      window.__sroEffect(
        JSON.stringify({ of, of_at, effect, frame_path: framePathOf(window), url: location.href }),
      );
    } catch {}
  };

  const OUTLINES_PER_GESTURE = 3;
  const OUTLINED = 'form, dialog, [role=dialog], [role=alertdialog], [role=form], [role=alert], [role=status]';
  let seenOutline = null;
  let outlines = [];
  const takeOutline = () => {
    let taken = null;
    try {
      taken = JSON.stringify(outlineOf(document));
    } catch {
      return;
    }
    if (taken === seenOutline) return;
    seenOutline = taken;
    outlines = [...outlines, JSON.parse(taken)].slice(-OUTLINES_PER_GESTURE);
  };
  const appeared = (change) => {
    const inside = change.target.nodeType === 1 ? change.target : change.target.parentElement;
    if (inside && inside.closest('[role=alert], [role=status]')) return true;
    return [...change.addedNodes].some(
      (node) => node.nodeType === 1 && (node.matches(OUTLINED) || node.querySelector(OUTLINED)),
    );
  };
  const WATCHING = '__sroOutlineWatch';
  if (window[WATCHING]) window[WATCHING].disconnect();
  window[WATCHING] = new MutationObserver((changes) => {
    if (changes.some(appeared)) takeOutline();
  });
  window[WATCHING].observe(document, { childList: true, subtree: true, characterData: true });

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

  // Best-effort label. The authoritative accessible name comes from the AX tree.
  // Never for a credential field.
  const label = (el) => (isSecretField(el) ? null : nameOf(el) || null);

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
    const cmp = cmpOf(el);
    if (!cmp) return null;
    const chain = chainOf(el);
    // Two segments: enough context to disambiguate, short enough to survive a
    // screen being re-parented, which happens whenever a dialog is involved.
    const query = chain.slice(-2).join(' ');
    return {
      framework: 'extjs',
      xtype: cmp.getXType ? cmp.getXType() : cmp.xtype,
      itemId: cmp.itemId && !/^ext-/.test(cmp.itemId) ? cmp.itemId : null,
      name: cmp.name || null,
      fieldLabel: cmp.fieldLabel || null,
      // Ext's own word for it. `allowBlank: false` is how an Ext form declares
      // a field mandatory, and it is the only one of the three signals that is
      // true of a control the page renders with no star and no aria attribute
      // -- which this application does, on the two fields it does demand.
      required:
        cmp.allowBlank === false ? true : cmp.allowBlank === true ? false : null,
      text: typeof cmp.text === 'string' ? cmp.text.slice(0, MAX_TEXT) : null,
      query,
      chain,
    };
  };

  const describe = (el) => {
    if (!el || el.nodeType !== 1) return null;
    const secret = isSecretField(el);
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
    // Each new reader is guarded alone: a page that breaks one loses that key.
    const tried = (read, otherwise) => {
      try {
        return read();
      } catch {
        return otherwise;
      }
    };
    const sibling = tried(() => siblingOf(el), { index: null, count: null });
    return {
      tag: el.tagName.toLowerCase(),
      role: roleOf(el),
      name: label(el),
      secret,
      text: secret ? null : (el.innerText || '').trim().slice(0, MAX_TEXT) || null,
      testId:
        el.getAttribute('data-testid') ||
        el.getAttribute('data-test-id') ||
        el.getAttribute('data-test') ||
        null,
      // Whether the PAGE says this field must be filled.
      //
      // Three ways a form says it and this reads all three, because a page
      // that uses only one is the common case: `aria-required`, which
      // accessibility guidance asks for; the HTML5 attribute, which the
      // browser itself enforces; and the star on the label, which is what a
      // person sees and often the only one present.
      //
      // Until 2026-09-22 only the star was captured, in the label text, and
      // nothing read it -- so a job demanded every field two demonstrations
      // happened to vary, and an operator with no Manufacturer to give could
      // not run the job at all. The star is the weakest of the three: screen
      // readers skip it as punctuation, which is exactly why the other two
      // exist.
      //
      // `null` where nothing said, which reads downstream as optional. A page
      // marking required fields by colour alone tells this system nothing,
      // and guessing from a colour is how a run stops for a field nobody has
      // to fill.
      required: requiredOf(el),
      cssPath: cssPath(el),
      xpath: xpathOf(el),
      bounds: boundsOf(el),
      attributes,
      component: component(el),
      landmarks: landmarksOf(el),
      labelText: secret ? null : tried(() => labelOf(el) || null, null),
      fullName: secret ? null : tried(() => fullNameOf(el), null),
      siblingIndex: sibling.index,
      siblingCount: sibling.count,
    };
  };

  const placeNow = () => {
    try {
      return placeOf(document);
    } catch {
      return null;
    }
  };
  const choiceNow = (el) => {
    try {
      return choiceOf(el);
    } catch {
      return null;
    }
  };

  const modifiers = (e) => {
    const mods = [];
    if (e.ctrlKey) mods.push('ctrl');
    if (e.shiftKey) mods.push('shift');
    if (e.altKey) mods.push('alt');
    if (e.metaKey) mods.push('meta');
    return mods;
  };

  const emit = (record, el = null) => {
    if (watching) watching.finish('next');
    const at = Date.now() / 1000;
    count += 1;
    const ref = `${REALM}.${count}`;
    const prior = last ? stateOf(last) : null;
    const prior_of = last ? lastRef : null;
    takeOutline();
    const sent = outlines;
    outlines = [];
    last = el;
    lastRef = el ? ref : null;
    try {
      window.__sroRecord(
        JSON.stringify({
          ...record,
          ref,
          prior,
          prior_of,
          outlines: sent,
          place: placeNow(),
          frame_path: framePathOf(window),
          at,
          url: location.href,
        }),
      );
    } catch {
      seenOutline = null;
      // The binding is not installed yet, or the frame is being torn down.
      // Losing a gesture is preferable to breaking the page the operator is using.
    }
    try {
      watching = watchEffect(window, sendEffect(ref, at));
    } catch {
      watching = null;
    }
  };

  listen('sro:dropped', (e) => {
    // `detail` names the dropped gesture's ref, or `null` when it was refused
    // for size before it could be parsed and given one -- either way, it is
    // always the gesture just recorded, so both mean "forget it".
    if (e.detail === null || e.detail === lastRef) {
      last = null;
      lastRef = null;
    }
    seenOutline = null;
  });

  listen('click', (e) =>
    emit(
      {
        kind: 'click',
        target: describe(e.target),
        modifiers: modifiers(e),
        detail: e.detail,
        trusted: e.isTrusted,
        choice: choiceNow(e.target),
      },
      e.target,
    ),
  );

  // One event per completed edit rather than per keystroke: `change` fires on
  // blur, so the value recorded is what the human settled on.
  listen('change', (e) => {
    const el = e.target;
    if (!el) return;
    if (el.type === 'file' && el.files) {
      emit(
        {
          kind: 'upload',
          target: describe(el),
          value: [...el.files].map((file) => file.name).join(', ').slice(0, MAX_VALUE),
          modifiers: [],
        },
        el,
      );
      return;
    }
    const kind = el.tagName === 'SELECT' ? 'select' : 'type';
    const secret = isSecretField(el);
    emit(
      {
        kind,
        target: describe(el),
        value: secret ? null : (el.value == null ? null : String(el.value).slice(0, MAX_VALUE)),
        secret,
        modifiers: [],
      },
      el,
    );
  });

  listen('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey || e.altKey) && e.key.length === 1 && watching) {
      watching.shortcut([...modifiers(e), e.key.toLowerCase()].join('+'));
    }
    // Only keys that commit or cancel. Every other keystroke arrives as the
    // `change` value above.
    if (!['Enter', 'Escape', 'Tab'].includes(e.key)) return;
    emit(
      { kind: 'press', target: describe(e.target), value: e.key, modifiers: modifiers(e) },
      e.target,
    );
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
