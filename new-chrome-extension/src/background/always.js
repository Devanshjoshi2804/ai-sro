// Which systems are watched wherever they open.
//
// Watching used to be a fact about a TAB: somebody pressed "Watch this tab"
// and that tab, until it closed, was evidence. Every other tab on the same
// system was blind -- a link opened in a new tab, a window reopened after
// lunch, and the tab a RUN opens for itself.
//
// Measured on the deployment, 2026-09-17: a run drove a Blue Yonder tab it had
// opened, with the orange "AI-SRO is working in this tab" banner across the
// top of it, while the panel beside it said `not watched`. Nothing the run did
// was recorded. The job performed and the system learnt nothing from it, which
// is the whole loop this product is.
//
// So the operator says it once about the SYSTEM -- "always watch this site" --
// and every tab on that host is watched from the moment it commits a page,
// however it came to exist. A host nobody has said that about behaves exactly
// as it did: the panel offers, and a press watches that one tab.
//
// Pure: given a url and the list, say whether it is watched. Nothing here
// touches storage or Chrome.

/** The host of a url, or "" for anything that is not a page. */
export function hostOf(url) {
  try {
    const { protocol, hostname } = new URL(url);
    return /^https?:$/.test(protocol) ? hostname : "";
  } catch {
    return "";
  }
}

/**
 * Whether this url is on a system the operator watches everywhere.
 *
 * Exact hosts. A pattern language here would be a second matcher to keep in
 * step with the tenant policy's `exclude_hosts`, and the thing being decided
 * -- "is this the warehouse I said to watch" -- is answered by the name the
 * browser is showing.
 */
export function alwaysWatched(url, hosts) {
  const host = hostOf(url);
  return Boolean(host) && (hosts || []).includes(host);
}

/** The list with this host in it, once. */
export function alsoWatch(host, hosts) {
  const kept = (hosts || []).filter((one) => one && one !== host);
  return host ? [host, ...kept] : kept;
}
