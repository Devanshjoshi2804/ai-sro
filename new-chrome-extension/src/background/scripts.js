// Where the recorder is allowed to run.
//
// The policy is enforced by *not registering* a content script on an excluded
// host, rather than by injecting one and filtering afterwards. An excluded page
// is untouched: nothing of ours runs on it, so there is nothing to leak, to
// filter, or to get wrong later. ADR 008.

const ID = "sro-observe";
const MAIN_ID = "sro-observe-main";
const WATCH_ID = "sro-watch";

const ALL = ["http://*/*", "https://*/*"];

/** The isolated world's half: the policy-checked relay and the request patch's
 * receiving end. Order matters -- sensitivity.generated.js puts the credential
 * rules on this world's window before network.js, which refuses to store a body
 * it cannot check them against. */
const ISOLATED = [
  "src/content/sensitivity.generated.js",
  "src/content/observe.js",
  "src/content/network.js",
];

/** The page's own realm: the network patch must be the `fetch` the page
 * actually calls, and the recorder identifies a control through the
 * framework's `Ext` registry, which does not exist in an isolated world. */
const MAIN = [
  "src/content/recorder-bridge.main.js",
  "src/content/recorder.generated.js",
  "src/content/network.main.js",
];

/** What the operator's own browser evaluates a mail rule with.
 *
 * Registered separately from the two above and on the watch hosts only, which
 * is the whole of its permission: a mail host is excluded from capture on
 * purpose (ADR 008) and stays excluded. This reads a sender, a subject and the
 * values the operator marked, decides in the page, and forgets. Nothing about
 * a mail is queued, uploaded or screenshotted -- `watch.js` never touches the
 * queue and has no way to.
 */
const WATCH = ["src/content/watch.js"];

/** `*.example.com` and `example.com` both mean the host and its subdomains. */
function patternsFor(host) {
  const bare = host.replace(/^\*?\./, "");
  return [`*://${bare}/*`, `*://*.${bare}/*`];
}

/** RFC 6265 domain-match, the one the backend's `domain_matches` makes: the
 * host itself or a subdomain of it, never a suffix test. One definition,
 * because `allowsHost` and the watch host check are the same question and
 * three copies of this rule disagreed once. */
export function hostMatches(hostname, pattern) {
  const bare = String(pattern || "")
    .replace(/^\*?\./, "")
    .replace(/\.+$/, "")
    .toLowerCase();
  const host = String(hostname || "")
    .replace(/\.+$/, "")
    .toLowerCase();
  if (!host || !bare) return false;
  return host === bare || host.endsWith(`.${bare}`);
}

export async function applyPolicy(policy, { on, granted = [] }) {
  // Only the two ids this function owns. `unregister()` defaults to all three
  // because sign-out means stop everything, and a policy change is not that:
  // withdrawing the watch script here would have every heartbeat that carried
  // a new policy version quietly stop the watching, and nothing says so --
  // the panel keeps listing the watch, and the mails simply stop matching.
  await unregister([ID, MAIN_ID]);
  if (!on || !policy) return;

  const matches = policy.include_hosts?.length
    ? policy.include_hosts.flatMap(patternsFor)
    : ALL;
  // A granted host is one the operator asked to watch, so it must actually
  // get a script. Its patterns come out of the exclusion rather than being
  // added to `matches`: an `include_hosts` tenant has named the only hosts
  // that may be observed, and a grant does not widen that list -- the same
  // line the backend's `ObservationPolicy.allows` draws.
  const excludeMatches = (policy.exclude_hosts || [])
    .flatMap(patternsFor)
    .filter((pattern) => !granted.some((host) => patternsFor(host).includes(pattern)));

  await chrome.scripting.registerContentScripts([
    {
      id: ID,
      // Order matters: sensitivity.generated.js puts the credential rules on
      // this world's window before network.js, which refuses to store a body
      // it cannot check them against.
      js: ISOLATED,
      matches,
      excludeMatches,
      // Both deliberate: `document_start` so the page's own scripts are not
      // already running when we install, and every frame because DOM events do
      // not cross a frame boundary and this WMS is iframes all the way down.
      runAt: "document_start",
      allFrames: true,
      persistAcrossSessions: false,
    },
    {
      id: MAIN_ID,
      // The page's own realm, not the extension's isolated one. Both of these
      // need the application's own globals: the network patch must be the
      // `fetch` the page actually calls, and the recorder identifies a control
      // through the framework's `Ext` registry, which does not exist in an
      // isolated world. Each hands its result to the isolated world over a
      // CustomEvent. Same matches/excludeMatches: an excluded page gets no
      // capture of any kind, not just gestures.
      js: MAIN,
      matches,
      excludeMatches,
      runAt: "document_start",
      allFrames: true,
      world: "MAIN",
      persistAcrossSessions: false,
    },
  ]);
}

/** Registers the watch script on exactly the hosts that have a watch.
 *
 * Its own id, its own call: watches change when a trigger is created and the
 * policy changes on a heartbeat, and neither may take the other's script down.
 */
export async function applyWatches(hosts) {
  await unregister([WATCH_ID]);
  const wanted = [...new Set((hosts || []).filter(Boolean))];
  if (!wanted.length) return;
  await chrome.scripting.registerContentScripts([
    {
      id: WATCH_ID,
      js: WATCH,
      matches: wanted.flatMap(patternsFor),
      // `document_idle`, not `document_start`: there is no page of ours to get
      // in front of here, and a mail client has rendered nothing to read at
      // document_start. Isolated world, because reading a marked node is a DOM
      // question and the page's own globals are not wanted anywhere near it.
      runAt: "document_idle",
      // ponytail: the top document only. A client that renders the message
      // body in an iframe needs allFrames, and with it a match in two frames
      // is two offers -- worth the dedup only once a real client needs it.
      allFrames: false,
      persistAcrossSessions: false,
    },
  ]);
}

export async function unregister(ids = [ID, MAIN_ID, WATCH_ID]) {
  const registered = await chrome.scripting.getRegisteredContentScripts({ ids });
  if (registered.length) {
    await chrome.scripting.unregisterContentScripts({ ids: registered.map((s) => s.id) });
  }
}

export async function registeredOn() {
  const [script] = await chrome.scripting.getRegisteredContentScripts({ ids: [ID] });
  return script ? { matches: script.matches, excludeMatches: script.excludeMatches || [] } : null;
}

/** Same include/exclude rule as the content-script registration above, for
 * events (webNavigation) that never go through a registered script to enforce
 * it by absence. An excluded host must produce zero rows of every kind. */
export function allowsHost(url, policy, granted = []) {
  if (!policy) return false;
  let parsed;
  try {
    parsed = new URL(url);
  } catch {
    return false;
  }
  // The registration above matches http and https and nothing else, so those
  // are the only schemes this may answer yes to. Without the check a
  // `chrome://settings/passwords` visit has hostname "settings", matches no
  // exclusion, and gets recorded -- as does the full path of a `file://` URL,
  // on pages where no content script of ours has ever run.
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return false;
  const hostname = parsed.hostname;
  const matchesHost = (pattern) => hostMatches(hostname, pattern);
  const included = !policy.include_hosts?.length || policy.include_hosts.some(matchesHost);
  // Exactly the host somebody pressed the button about, never a subdomain of
  // it: `hostMatches` is right for a policy pattern an administrator wrote and
  // wrong for a grant, where reading one mailbox as a whole domain would admit
  // every host under it. The backend compares the same way.
  const excluded =
    (policy.exclude_hosts || []).some(matchesHost) && !granted.includes(hostname);
  return included && !excluded;
}

/** Put the recorder into a tab that is already open.
 *
 * Registration only injects on the *next* navigation, so a tab open before the
 * operator pressed "watch" -- or before the extension was last reloaded -- runs
 * nothing of ours and records nothing, however clearly the panel says it is
 * watching. Telling somebody to reload the page they are working in is not an
 * answer: they lose the form they had half filled in.
 *
 * Safe on a tab that already has them, and each file is what makes it so.
 *
 * `executeScript` RUNS THE FILE, every time it is called. This docstring used
 * to say "Chrome does not run a file it has already put in a frame", which is
 * true of a REGISTERED content script and false of this -- so every one of
 * these files is re-executed on a policy refresh, on an extension reload, and
 * on a second press of "watch", in every frame of the tab.
 *
 * Each of them therefore asks, first thing, whether a copy that can still
 * reach the worker is already in residence: `network.js` and `observe.js` by
 * name, the page-realm patch by refusing a fetch it has already patched. Not
 * a plain "already installed" flag -- an orphaned copy left by an extension
 * reload can forward nothing, and a flag it had set would keep the live
 * replacement out.
 *
 * `observe.js` had no guard and did not need one BY ACCIDENT: its top-level
 * `const` threw on the second execution, which is a SyntaxError doing the work
 * of a condition, and which filled the extension's error list with forty of
 * them. It asks the question properly now.
 *
 * `test_watching_a_tab_that_was_already_open_needs_no_reload` holds the
 * outcome: pressing "watch" twice records one copy of a gesture.
 */
export async function injectInto(tabId, url, policy, granted = []) {
  if (!allowsHost(url, policy, granted)) return false;
  const into = { tabId, allFrames: true };
  try {
    await chrome.scripting.executeScript({ target: into, files: ISOLATED });
    await chrome.scripting.executeScript({ target: into, files: MAIN, world: "MAIN" });
    return true;
  } catch {
    // A tab that navigated away mid-injection, or a page Chrome will not let
    // anyone script (the web store, a PDF viewer). Watching it is still
    // recorded -- the next navigation injects normally.
    return false;
  }
}


/** Put the recorder back into every tab this browser is already watching.
 *
 * Reloading the extension severs `chrome.runtime` for every content script
 * already in a page. The script cannot report that -- there is nobody left to
 * report it to -- so the tab goes quiet, while the panel goes on saying
 * "watching this tab, since 65m", because the watch is a fact about the tab and
 * not about whether anything is still listening.
 *
 * An operator who reloads the extension, demonstrates a task and finds nothing
 * was recorded learns exactly one thing, and it is not a good one.
 *
 * Registration does not cover this: it governs the next navigation only, so a
 * tab open across the reload runs nothing of ours until it is navigated. And
 * telling somebody to reload the page they are working in is not an answer --
 * they lose the form they had half filled in.
 *
 * Safe to run on every worker start, which is the only way it can run at all:
 * there is no way to tell a reload from an ordinary wake-up, and a tab that
 * still has the scripts is unharmed -- the page-realm patch refuses a `fetch`
 * it has already patched, and Chrome does not run a file it has already put in
 * a frame.
 */
export async function injectIntoWatched(tabs, policy, granted = []) {
  const put = await Promise.all(
    (tabs || []).map(async (tab) => {
      // A watch outlives the tab it names -- a closed tab, or one Chrome hands
      // the same id to later. Reading the tab back is what tells the two apart,
      // and a watch on a tab that is gone is not one to inject into.
      const live = await chrome.tabs.get(tab.tabId).catch(() => null);
      if (!live?.url) return false;
      return await injectInto(tab.tabId, live.url, policy, granted);
    }),
  );
  return put.filter(Boolean).length;
}
