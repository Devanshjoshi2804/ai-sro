// Just enough document to build a panel in, and to read it back out of.
//
// Every module under `panel/` is a pure function of some state to DOM, which is
// what makes them testable in plain node with no browser and no bundler. They
// all need the same handful of properties, so it is written once here rather
// than copied into each self-check -- six copies of a fake drift, and a fake
// that drifts is a test asserting on something the code never does.
//
// `panel.test.mjs` keeps its own: it runs the real `panel.js` inside a vm, so
// its document has to exist inside that sandbox rather than in this realm.

/** Every `innerHTML =` any node built here was ever given.
 *
 * A fake document parses nothing, so asking it "did an `<img>` appear?" gets
 * the same answer -- none -- whether the code under test wrote `textContent` or
 * `innerHTML`. What it can see is the assignment itself, so that is what the
 * security checks assert on: this list staying empty is the property, and it is
 * one the fake cannot be wrong about.
 */
export const asMarkup = [];

export function node(tag) {
  return {
    tag,
    className: "",
    dataset: {},
    type: "",
    value: "",
    placeholder: "",
    disabled: false,
    hidden: false,
    textContent: "",
    kids: [],
    listeners: {},
    set innerHTML(value) {
      asMarkup.push({ tag: this.tag, value });
    },
    get innerHTML() {
      return "";
    },
    append(...added) {
      this.kids.push(...added);
    },
    prepend(...added) {
      this.kids.unshift(...added);
    },
    remove() {
      this.removed = true;
    },
    addEventListener(kind, fn) {
      (this.listeners[kind] ??= []).push(fn);
    },
    // Attributes the platform has and a plain object does not. Only what a
    // panel module actually sets -- `aria-expanded` on a control that folds --
    // rather than a general attribute bag: this fake exists to be simple
    // enough that it cannot itself be the thing that is wrong.
    attributes: {},
    setAttribute(name, value) {
      this.attributes[name] = String(value);
    },
    getAttribute(name) {
      return Object.hasOwn(this.attributes, name) ? this.attributes[name] : null;
    },
    querySelectorAll(selector) {
      const all = [];
      const walk = (el) => {
        if (el.tag === selector) all.push(el);
        for (const kid of el.kids) walk(kid);
      };
      walk(this);
      return all;
    },
  };
}

/** Install it, before importing the module under test.
 *
 * Called at the top of a self-check rather than assigned by each of them, so
 * "which globals does a panel module need" is answered in one place.
 */
export function install() {
  globalThis.document = { createElement: node };
}

/** Every word a node and its children carry, the way a person reads it. */
export function words(el) {
  return [el.textContent, ...el.kids.map(words)].join(" ").replace(/\s+/g, " ").trim();
}

/** Every descendant with this tag, in document order. */
export function of(el, tag) {
  return el.querySelectorAll(tag);
}
