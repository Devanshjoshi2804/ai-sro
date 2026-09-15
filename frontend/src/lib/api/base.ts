import { env } from "@/lib/env";

/** The API's websocket origin, whether it was configured absolutely or not.
 *
 * `NEXT_PUBLIC_API_URL` may be a path now -- `/api`, behind a proxy that
 * serves the console and the API from one origin. `fetch` is happy with that;
 * `new WebSocket()` is not, and refuses anything without a scheme. The old
 * `.replace(/^http/, "ws")` turned an absolute url into a websocket one and
 * turned `/api` into `/api`, which fails at the point of connection with a
 * message about the url rather than about the configuration.
 *
 * Resolved against the page's own origin, which is exactly what same-origin
 * means and is only available in the browser -- every caller is a client
 * component opening a socket.
 */
export function apiWebsocketBase(): string {
  const absolute = new URL(env.NEXT_PUBLIC_API_URL, window.location.origin);
  // `https` -> `wss` falls out of the same replacement.
  return absolute.toString().replace(/\/$/, "").replace(/^http/, "ws");
}
