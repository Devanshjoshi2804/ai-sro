/**
 * The same socket, dialled at the rig.
 *
 * The rig is the model-first architecture's own process, and a run it starts
 * has to reach a browser. It gets the backend's channel verbatim -- keepalive,
 * exactly-once answering, backoff -- pointed at `state.rigUrl()`.
 *
 * No device secret: the rig has one token and no device registry, and offers
 * `["bearer", rigToken]`. An empty rig url dials nothing, silently. The rig is
 * optional; its absence is not the extension's problem.
 *
 * **This whole module goes in phase 5's rig-settings task**, along with the
 * two settings it reads. `channel.js` and `createChannel` stay: this is a
 * caller, not the implementation.
 */
import { createChannel } from "./channel.js";
import { isRigUrl, state } from "./state.js";

const rig = createChannel({
  describe: "rig",
  async dial() {
    const [rigUrl, rigToken, deviceId] = await Promise.all([
      state.rigUrl(),
      state.rigToken(),
      state.deviceId(),
    ]);
    if (!isRigUrl(rigUrl) || !rigToken || !deviceId) return null;
    return {
      url: `${rigUrl.replace(/^http/, "ws")}/v1/agents/${encodeURIComponent(deviceId)}/commands`,
      protocols: ["bearer", rigToken],
    };
  },
});

export const status = rig.status;
export const settle = rig.settle;
export const close = rig.close;
// The rig holds a command against `busy` the same way the backend does
// (`new_agent_arch/src/rig/channel.py`), and a rig-dispatched command lands in
// the middle of somebody typing exactly as a backend-dispatched one does.
export const operatorIsWorking = rig.operatorIsWorking;
