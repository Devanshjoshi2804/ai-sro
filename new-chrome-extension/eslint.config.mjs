// One rule: a name this code uses is a name it can reach.
//
// `node --check` validates syntax and nothing else, so a module that calls a
// function it forgot to import passes every check this extension had and throws
// `ReferenceError` at runtime -- on the first message the worker handles, which
// is sign-in, which means the extension does not start at all. That happened:
// an import line was written against `import { state } from "./state.js"` when
// the file says `import { capturing, state }`, the edit silently did nothing,
// and thirty-six browser tests errored on a `KeyError: 'capturing'` three layers
// from the cause.
//
// Deliberately not a style config. This extension has no build step and no
// formatter of its own, and adding one would be a change to every file for the
// sake of a rule nobody asked for. `no-undef` is the one that would have caught
// a defect that shipped.

const browser = {
  chrome: "readonly",
  window: "readonly",
  document: "readonly",
  navigator: "readonly",
  location: "readonly",
  console: "readonly",
  fetch: "readonly",
  crypto: "readonly",
  performance: "readonly",
  atob: "readonly",
  btoa: "readonly",
  setTimeout: "readonly",
  clearTimeout: "readonly",
  setInterval: "readonly",
  clearInterval: "readonly",
  queueMicrotask: "readonly",
  structuredClone: "readonly",
  URL: "readonly",
  URLSearchParams: "readonly",
  Blob: "readonly",
  FormData: "readonly",
  Headers: "readonly",
  Request: "readonly",
  Response: "readonly",
  AbortController: "readonly",
  AbortSignal: "readonly",
  TextEncoder: "readonly",
  TextDecoder: "readonly",
  CustomEvent: "readonly",
  Event: "readonly",
  EventTarget: "readonly",
  FocusEvent: "readonly",
  KeyboardEvent: "readonly",
  MouseEvent: "readonly",
  PointerEvent: "readonly",
  MutationObserver: "readonly",
  XMLHttpRequest: "readonly",
  WebSocket: "readonly",
  indexedDB: "readonly",
  IDBKeyRange: "readonly",
  self: "readonly",
  globalThis: "readonly",
  CSS: "readonly",
  Node: "readonly",
  NodeFilter: "readonly",
  Image: "readonly",
  HTMLElement: "readonly",
  getComputedStyle: "readonly",
  requestAnimationFrame: "readonly",
  ReadableStream: "readonly",
  DOMParser: "readonly",
  Element: "readonly",
  HTMLInputElement: "readonly",
  HTMLTextAreaElement: "readonly",
  HTMLSelectElement: "readonly",
};

export default [
  {
    files: ["src/**/*.js", "src/**/*.mjs", "scripts/**/*.mjs"],
    languageOptions: {
      ecmaVersion: 2024,
      sourceType: "module",
      globals: browser,
    },
    linterOptions: { reportUnusedDisableDirectives: true },
    // `no-dupe-keys` for the same reason `no-undef` is here: the wire
    // whitelists in `api.js` are long object literals, one key was written
    // into one of them twice, and the later copy silently won. Nothing said
    // so, and the field a card draws is exactly the thing nobody notices is
    // being drawn from the wrong line.
    rules: { "no-undef": "error", "no-dupe-keys": "error" },
  },
  {
    // The application's own framework, read from the page's realm. Not ours to
    // declare and not ours to assume is there either -- every use of it in the
    // recorder is guarded, which is the part that matters.
    files: ["src/content/recorder.generated.js", "src/content/*.main.js"],
    languageOptions: { globals: { ...browser, Ext: "readonly" } },
  },
  {
    // Test files and the scripts run in node and reach for its own globals.
    files: ["src/**/*.test.mjs", "scripts/**/*.mjs"],
    languageOptions: {
      globals: {
        ...browser,
        process: "readonly",
        Buffer: "readonly",
        __dirname: "readonly",
        // Node's own, and the panel's tests reach for it: a fake that must let
        // the microtask queue drain waits a TICK rather than a millisecond,
        // and `setTimeout(0)` is not the same thing.
        setImmediate: "readonly",
      },
    },
  },
];
