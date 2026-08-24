// Gives recorder.generated.js somewhere to hand a gesture, in the page's realm.
//
// The recorder has to run in the page's own JavaScript realm: it identifies an
// ExtJS control through `window.Ext`, and from an isolated world `window.Ext`
// is the *isolated* world's window, where the application's globals do not
// exist. Registered there instead, it went looking for `Ext`, never found it,
// and every gesture shipped `component: null` -- which is the one locator this
// WMS has that survives a reload, since its DOM ids are assigned in render
// order.
//
// Being in the page's realm means no chrome.* here, so a gesture crosses to
// the isolated world the same way a captured request does: a CustomEvent on
// window, the one channel the two realms share.
(() => {
  window.__sroRecord = (json) => {
    window.dispatchEvent(new CustomEvent("sro:gesture", { detail: json }));
  };
})();
