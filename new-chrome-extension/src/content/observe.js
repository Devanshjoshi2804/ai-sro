// The capture entry point. A2 injects the page recorder from here; for now it
// does the one thing the skeleton has to prove -- that it is running on a page
// the policy allows, and on no other.

chrome.runtime.sendMessage({ kind: "content-ready", url: location.href }).catch(() => {
  // The worker is asleep and this page is not worth waking it for.
});
