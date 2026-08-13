import { chromium } from 'playwright';
import { goto, resetToGrid, clickButton } from './ext.mjs';
const [route, fieldName] = process.argv.slice(2);
const b = await chromium.connectOverCDP('http://localhost:9222');
const page = b.contexts()[0].pages().find(p=>p.url().includes('jdadelivers')) || b.contexts()[0].pages()[0];
const frame = await goto(page, route);
await resetToGrid(page, frame); await page.waitForTimeout(1200);
await clickButton(frame, page, { itemId: 'addButton' }); await page.waitForTimeout(3800);
console.log(JSON.stringify(await page.evaluate((fn)=>{
  const f=document.querySelector('iframe'); const w=f.contentWindow;
  const forms=w.Ext.ComponentQuery.query('form').filter(x=>{const d=x.getEl&&x.getEl()&&x.getEl().dom;const r=d&&d.getBoundingClientRect();return r&&r.width>0;});
  const form=forms[forms.length-1].getForm();
  const fld=form.findField(fn);
  if(!fld) return {error:'not found'};
  const store=fld.getStore&&fld.getStore();
  return {
    xtype: fld.xtype, name: fld.name, valueField: fld.valueField, displayField: fld.displayField,
    hasStore: !!store, storeCount: store&&store.getCount?store.getCount():null,
    sample: store&&store.getCount&&store.getCount()>0 ? store.getAt(0).data : null,
    methods: Object.getOwnPropertyNames(Object.getPrototypeOf(fld)).filter(m=>/set|select|pick|search/i.test(m)).slice(0,25),
    subFields: (fld.query? fld.query('field').map(x=>({name:x.name,xtype:x.xtype,label:x.fieldLabel})) : null),
  };
}, fieldName), null, 1));
await b.close();
