import { withPage } from './api.mjs';
console.log(JSON.stringify(await withPage((page) => page.evaluate(() => {
  const f = document.querySelector('iframe'); const w = f.contentWindow;
  const forms = w.Ext.ComponentQuery.query('form');
  const form = forms[forms.length - 1];
  if (!form) return { error: 'no form' };
  return {
    url: w.location.hash.slice(0, 80),
    fields: form.getForm().getFields().items.map(x => ({
      name: x.name, label: x.fieldLabel, value: x.getValue(),
      valid: x.isValid(), errors: x.getErrors ? x.getErrors() : null,
      allowBlank: x.allowBlank,
    })).filter(x => !x.valid || x.allowBlank === false),
  };
})), null, 1));
