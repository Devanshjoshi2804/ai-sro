// Whether two urls name the same screen.
//
// Its own module because two callers need it and neither may import the
// other: `commands.js` is the whole command surface and `recognise.js` is
// pure arithmetic the tests run without a browser.

/** Two URLs that are the same screen.
 *
 * Compared without the query, because a session id or a site code in it is not
 * what makes this the Work Areas page -- and with the fragment, because in an
 * application that routes on the fragment it is the only thing that says which
 * screen this is at all.
 */
export function samePage(a, b) {
  const parse = (raw) => {
    try {
      const url = new URL(raw);
      return `${url.origin}${url.pathname}${url.hash}`.replace(/\/+$/, "");
    } catch {
      return null;
    }
  };
  const one = parse(a);
  return one !== null && one === parse(b);
}
