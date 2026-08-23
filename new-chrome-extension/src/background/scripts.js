// Where the recorder is allowed to run.
//
// The policy is enforced by *not registering* a content script on an excluded
// host, rather than by injecting one and filtering afterwards. An excluded page
// is untouched: nothing of ours runs on it, so there is nothing to leak, to
// filter, or to get wrong later. ADR 008.

const ID = "sro-observe";

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
      js: ["src/content/observe.js"],
      matches,
      excludeMatches,
      // Both deliberate: `document_start` so the page's own scripts are not
      // already running when we install, and every frame because DOM events do
      // not cross a frame boundary and this WMS is iframes all the way down.
      runAt: "document_start",
      allFrames: true,
      persistAcrossSessions: false,
    },
  ]);
}

export async function unregister() {
  const registered = await chrome.scripting.getRegisteredContentScripts({ ids: [ID] });
  if (registered.length) {
    await chrome.scripting.unregisterContentScripts({ ids: [ID] });
  }
}

export async function registeredOn() {
  const [script] = await chrome.scripting.getRegisteredContentScripts({ ids: [ID] });
  return script ? { matches: script.matches, excludeMatches: script.excludeMatches || [] } : null;
}
