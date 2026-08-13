/*
 * ext.mjs — reliable interaction helpers for this ExtJS SPA.
 *
 * The problem these solve: the app never tears down a visited screen. After browsing a few
 * routes, Ext.ComponentQuery.query('button') returns ~20 live `addButton` instances and a dozen
 * `Save` labels, nearly all belonging to cached, off-screen views. Selecting by visible text
 * therefore hits the wrong component or times out — the failure that made a Clients capture
 * report 'no visible Add' on a screen that plainly had one.
 *
 * Approach: resolve the target through the ExtJS component tree, keep only the instance whose
 * DOM node is actually rendered with a non-zero box, then issue a REAL click on that node by id.
 * Real events, correct target.
 */

/* Resolve the id of the single on-screen DOM node for an ExtJS button. */
export const findButtonId = (page, { itemId, text }) => page.evaluate(({ itemId, text }) => {
  const f = document.querySelector('iframe');
  const w = f && f.contentWindow && f.contentWindow.Ext ? f.contentWindow : window;
  const hits = w.Ext.ComponentQuery.query('button').filter((b) => {
    if (b.isDestroyed || b.disabled) return false;
    if (itemId && b.itemId !== itemId) return false;
    if (text && String(b.text || '').trim() !== text) return false;
    if (!b.isVisible || !b.isVisible()) return false;
    const el = b.getEl && b.getEl();
    const dom = el && el.dom;
    if (!dom) return false;
    const r = dom.getBoundingClientRect();
    // A cached view still reports isVisible() true; only a real box proves it is on screen.
    return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < (w.innerHeight || 900);
  });
  return hits.length ? { id: hits[hits.length - 1].getEl().dom.id, count: hits.length } : null;
}, { itemId, text });

export async function clickButton(frame, page, sel, timeout = 15000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    const hit = await findButtonId(page, sel);
    if (hit) {
      await frame.locator('#' + hit.id).click({ timeout: 5000 });
      return hit;
    }
    await page.waitForTimeout(500);
  }
  throw new Error(`no on-screen button for ${JSON.stringify(sel)}`);
}

/* Read the currently-rendered form: the last form whose element has a real box. */
export const activeForm = (page) => page.evaluate(() => {
  const f = document.querySelector('iframe');
  const w = f && f.contentWindow && f.contentWindow.Ext ? f.contentWindow : window;
  const forms = w.Ext.ComponentQuery.query('form').filter((x) => {
    const dom = x.getEl && x.getEl() && x.getEl().dom;
    if (!dom) return false;
    const r = dom.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  });
  if (!forms.length) return { error: 'no rendered form' };
  const form = forms[forms.length - 1].getForm();
  return {
    fields: form.getFields().items.map((x) => ({
      field: x.name, label: x.fieldLabel, required: x.allowBlank === false,
      type: x.xtype, value: typeof x.getValue === 'function' ? x.getValue() : null,
      valid: typeof x.isValid === 'function' ? x.isValid() : null,
      errors: x.getErrors ? x.getErrors() : null,
    })),
  };
});

/* Set model values directly. Combos and lookup fields ignore typed text unless the underlying
 * model value is set — the documented Carrier PRO Number trap, where a typed real carrier code
 * displays correctly but leaves the value null and Save then does nothing, silently. */
export const setFields = (page, fields, pickFirst, relax, relaxRadio) => page.evaluate(({ fields, pickFirst, relax, relaxRadio }) => {
  const f = document.querySelector('iframe');
  const w = f && f.contentWindow && f.contentWindow.Ext ? f.contentWindow : window;
  const forms = w.Ext.ComponentQuery.query('form').filter((x) => {
    const dom = x.getEl && x.getEl() && x.getEl().dom;
    const r = dom && dom.getBoundingClientRect();
    return r && r.width > 0 && r.height > 0;
  });
  if (!forms.length) return { error: 'no rendered form' };
  const form = forms[forms.length - 1].getForm();
  const applied = {};
  /*
   * wmAddress fields carry forceSelection with an EMPTY store: no typed value can ever validate
   * because there is nothing to select. The Clients screen proves the intent is to create a new
   * address from typed text (its Add fires POST /wm/addresses), so for these fields we drop
   * forceSelection and let the typed value stand. Same family as the known Carrier PRO Number
   * trap, where a real code displays but never binds.
   */
  for (const name of relax || []) {
    const fld = form.findField(name);
    if (fld) { fld.forceSelection = false; if (fld.validator) fld.validator = null; }
  }
  for (const [name, value] of Object.entries(fields || {})) {
    const fld = form.findField(name);
    if (!fld) { applied[name] = 'FIELD-NOT-FOUND'; continue; }
    /*
     * A wmAddress field's value is a full Address MODEL RECORD, not a string: passing text
     * leaves an empty phantom record behind and the field stays "required". Write the record's
     * own fields instead, which is what the address sub-form does when a user types into it.
     */
    if (fld.xtype === 'wmAddress' && value && typeof value === 'object') {
      let rec = fld.getValue();
      if (!rec || typeof rec.set !== 'function') { fld.setValue(value.addressName || ''); rec = fld.getValue(); }
      if (rec && typeof rec.set === 'function') {
        rec.set(value);
        if (fld.setRawValue) fld.setRawValue(value.addressName || '');
        if (typeof fld.validate === 'function') fld.validate();
        applied[name] = rec.get ? rec.get('addressName') : 'set';
        continue;
      }
    }
    fld.setValue(value);
    if (typeof fld.validate === 'function') fld.validate();
    applied[name] = fld.getValue();
  }
  /*
   * Radiogroups report no field name and validate as "You must select one item in this group",
   * so they are addressed by their visible label and satisfied by checking the first radio.
   */
  for (const label of (relaxRadio || [])) {
    const groups = w.Ext.ComponentQuery.query('radiogroup').filter((g) => g.fieldLabel === label);
    const g = groups[groups.length - 1];
    if (!g) { applied['radio:' + label] = 'GROUP-NOT-FOUND'; continue; }
    const radios = g.query ? g.query('radiofield') : [];
    if (!radios.length) { applied['radio:' + label] = 'NO-RADIOS'; continue; }
    radios[0].setValue(true);
    applied['radio:' + label] = radios[0].inputValue !== undefined ? radios[0].inputValue : true;
  }
  for (const name of pickFirst || []) {
    const fld = form.findField(name);
    if (!fld) { applied[name] = 'FIELD-NOT-FOUND'; continue; }
    const store = fld.getStore && fld.getStore();
    if (!store || !store.getCount || store.getCount() === 0) { applied[name] = 'EMPTY-STORE'; continue; }
    const rec = store.getAt(0);
    fld.setValue(rec.get(fld.valueField || 'code'));
    applied[name] = fld.getValue();
  }
  return {
    applied,
    invalid: form.getFields().items.filter((x) => x.allowBlank === false && !x.isValid())
      .map((x) => ({ field: x.name, label: x.fieldLabel, errors: x.getErrors ? x.getErrors() : null })),
  };
}, { fields, pickFirst, relax, relaxRadio });

export const appFrame = async (page) => {
  for (let i = 0; i < 30; i++) {
    const f = page.frames().find((fr) => fr.url().includes('jdadelivers') && fr !== page.mainFrame());
    if (f) return f;
    await page.waitForTimeout(500);
  }
  return page.mainFrame();
};

/* Hash routing only: a full load drops the OIDC session, and re-setting the current hash is a
 * router no-op that would strand us on a half-filled form from the previous run. */
/*
 * Return to a grid if a previous run left an Add/edit form open.
 *
 * The SPA restores the last view for a route, so a capture that ended on a half-filled form
 * makes the next run land on that form — where there is no Add button at all. Cancelling first
 * is what makes runs repeatable. A dirty form raises an unsaved-changes confirm, answered Yes.
 */
/*
 * Clear any blocking modal and its masks.
 *
 * A failed save raises an "Exception Occurred" messagebox over 6 stacked masks and leaves the
 * form spinning on "Saving...". Nothing underneath is clickable while it is up, so a single
 * screen's failure silently poisons every screen that runs after it - which is exactly what
 * happened to a 10-screen batch. Always clear before doing anything else, and report what was
 * cleared, because a dismissed exception is a finding, not noise.
 */
export async function dismissBlocking(page) {
  return page.evaluate(() => {
    const f = document.querySelector('iframe');
    const w = f && f.contentWindow && f.contentWindow.Ext ? f.contentWindow : window;
    if (!w.Ext) return { cleared: [], masks: 0 };
    const cleared = [];
    for (const c of w.Ext.ComponentQuery.query('[floating]').filter((x) => x.isVisible && x.isVisible())) {
      const text = (c.el && c.el.dom ? c.el.dom.innerText : '').replace(/\s+/g, ' ').slice(0, 200);
      cleared.push({ xtype: c.xtype, title: c.title || null, text });
      try { c.close ? c.close() : c.hide(); } catch (e) { /* keep clearing the rest */ }
    }
    // Masks can outlive their owner component; unmask the body explicitly.
    try { if (w.Ext.getBody && w.Ext.getBody().unmask) w.Ext.getBody().unmask(); } catch (e) {}
    const masks = w.document.querySelectorAll('.x-mask').length;
    return { cleared, masks };
  }).catch(() => ({ cleared: [], masks: 0, error: 'evaluate failed' }));
}

export async function resetToGrid(page, frame) {
  // Any modal must go first: while one is up, Cancel and every other control is unclickable.
  await dismissBlocking(page);
  for (let i = 0; i < 2; i++) {
    const cancel = await findButtonId(page, { itemId: 'cancelButton' });
    if (!cancel) return i > 0;
    await frame.locator('#' + cancel.id).click({ timeout: 4000 }).catch(() => {});
    await page.waitForTimeout(1200);
    const yes = await findButtonId(page, { itemId: 'yes' });
    if (yes) { await frame.locator('#' + yes.id).click({ timeout: 4000 }).catch(() => {}); await page.waitForTimeout(1500); }
  }
  return true;
}

export async function goto(page, route) {
  await page.evaluate(() => { window.location.hash = '#wm.config/wm.config.warehouse.warehouse////'; });
  await page.waitForTimeout(2200);
  await page.evaluate((h) => { window.location.hash = h; }, route);
  await page.waitForTimeout(4800);
  return appFrame(page);
}
