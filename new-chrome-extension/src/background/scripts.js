// Where the recorder is allowed to run.
//
// The policy is enforced by *not registering* a content script on an excluded
// host, rather than by injecting one and filtering afterwards. An excluded page
// is untouched: nothing of ours runs on it, so there is nothing to leak, to
// filter, or to get wrong later. ADR 008.

const ID = "sro-observe";
const MAIN_ID = "sro-observe-main";

const ALL = ["http://*/*", "https://*/*"];

/** `*.example.com` and `example.com` both mean the host and its subdomains. */
function patternsFor(host) {
  const bare = host.replace(/^\*?\./, "");
  return [`*://${bare}/*`, `*://*.${bare}/*`];
}

export async function applyPolicy(policy, { on }) {
  await unregister();
  if (!on || !policy) return;

  const matches = policy.include_hosts?.length
    ? policy.include_hosts.flatMap(patternsFor)
    : ALL;
  const excludeMatches = (policy.exclude_hosts || []).flatMap(patternsFor);

  await chrome.scripting.registerContentScripts([
    {
      id: ID,
      // Order matters: observe.js defines window.__sroRecord and
      // recorder.generated.js defines window.__sroIsSecretName before
      // network.js, which reads both, runs.
      js: ["src/content/observe.js", "src/content/recorder.generated.js", "src/content/network.js"],
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
      // The page's own realm, not the extension's isolated one -- see
      // network.main.js for why. Same matches/excludeMatches: an excluded
      // page gets no capture of any kind, not just gestures.
      js: ["src/content/network.main.js"],
      matches,
      excludeMatches,
      runAt: "document_start",
      allFrames: true,
      world: "MAIN",
      persistAcrossSessions: false,
    },
  ]);
}

export async function unregister() {
  const registered = await chrome.scripting.getRegisteredContentScripts({ ids: [ID, MAIN_ID] });
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
export function allowsHost(url, policy) {
  if (!policy) return false;
  let hostname;
  try {
    hostname = new URL(url).hostname;
  } catch {
    return false;
  }
  const matchesHost = (pattern) => {
    const bare = pattern.replace(/^\*?\./, "");
    return hostname === bare || hostname.endsWith(`.${bare}`);
  };
  const included = !policy.include_hosts?.length || policy.include_hosts.some(matchesHost);
  const excluded = (policy.exclude_hosts || []).some(matchesHost);
  return included && !excluded;
}
