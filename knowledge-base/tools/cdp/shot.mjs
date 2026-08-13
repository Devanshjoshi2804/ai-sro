import { chromium } from 'playwright';
const b = await chromium.connectOverCDP('http://localhost:9222');
const page = b.contexts()[0].pages().find(p=>p.url().includes('jdadelivers')) || b.contexts()[0].pages()[0];
await page.screenshot({ path: 'tmp-shots/current.png', fullPage: false });
const info = await page.evaluate(() => {
  const w = document.querySelector('iframe')?.contentWindow;
  const out = { url: location.hash.slice(0,90), topText: document.body.innerText.replace(/\s+/g,' ').slice(0,300) };
  if (w && w.Ext) {
    const vis = c => { const d=c.getEl&&c.getEl()&&c.getEl().dom; const r=d&&d.getBoundingClientRect(); return r&&r.width>0&&r.height>0; };
    out.floating = w.Ext.ComponentQuery.query('[floating]').filter(c=>c.isVisible&&c.isVisible())
      .map(c=>({xtype:c.xtype, title:c.title||null, text:(c.el&&c.el.dom?c.el.dom.innerText:'').replace(/\s+/g,' ').slice(0,200)}));
    out.masks = w.document.querySelectorAll('.x-mask').length;
    out.visibleMasks = [...w.document.querySelectorAll('.x-mask')].filter(m=>m.getBoundingClientRect().width>0).length;
    out.buttons = w.Ext.ComponentQuery.query('button').filter(b=>!b.isDestroyed&&vis(b)&&b.text).map(b=>b.text).slice(0,15);
  }
  return out;
});
console.log(JSON.stringify(info,null,1));
// NOTE: do not close - browser.close() over CDP closes pages a concurrent run is using.
process.exit(0);
