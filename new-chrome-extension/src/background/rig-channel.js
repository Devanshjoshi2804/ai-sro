/**
 * The same socket, dialled at the rig.
 *
 * The rig is the model-first architecture's own process: it mirrors this
 * browser's uploads already (mirror.js), and a run it starts has to reach a
 * browser too. It gets the backend's channel verbatim -- keepalive,
 * exactly-once answering, backoff -- pointed at `state.rigUrl()`.
 *
 * No device secret: the rig has one token and no device registry, and offers
 * `["bearer", rigToken]`. Empty rig url means what it means for the mirror --
 * nothing is dialled, silently. The rig is optional; its absence is not the
 * extension's problem.
 */
import { createChannel } from "./channel.js";
import { isMirrorable } from "./mirror.js";
import { state } from "./state.js";

const rig = createChannel({
  describe: "rig",
  async dial() {
    const [rigUrl, rigToken, deviceId] = await Promise.all([
      state.rigUrl(),
      state.rigToken(),
      state.deviceId(),
    ]);
    if (!isMirrorable(rigUrl) || !rigToken || !deviceId) return null;
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
