// The screen that has to be truthful. If it says observing, it is observing.

const $ = (id) => document.getElementById(id);

async function ask(message) {
  const answer = await chrome.runtime.sendMessage(message);
  if (answer?.error) throw new Error(answer.error);
  return answer;
}

function render(status) {
  $("headline").dataset.on = String(status.capturing);
  $("headline").textContent = status.capturing
    ? `Ready. ${(status.watched || []).length} tab${(status.watched || []).length === 1 ? "" : "s"} being watched -- pick one in the side panel, beside the tab you work in.`
    : `Not observing — ${status.because}.`;

  $("device").textContent = status.deviceId || "not registered";
  // Screenshots are named here because they are the most invasive thing this
  // extension collects, and an operator who cannot see that pictures of their
  // screen are being taken has not been told.
  $("policy").textContent = status.policy
    ? `version ${status.policy.version}, ${status.policy.capture_enabled ? "enabled" : "not enabled"} ` +
      `for your tenant, ${
        status.policy.capture_screenshots
          ? `screenshots up to ${status.policy.screenshot_max_per_minute ?? 20} a minute`
          : "no screenshots"
      }`
    : "none yet";
  // Whether work can reach this browser at all, which is a different question
  // from whether it is being observed -- and the screen should not make the
  // operator guess which one "connected" meant.
  $("channel").textContent =
    { open: "open — this browser can be given work", connecting: "dialling…" }[status.channel] ||
    "closed";
  $("beat").textContent = status.lastBeat
    ? new Date(status.lastBeat).toLocaleString()
    : "not yet";
  $("trouble").textContent = status.lastError || "none";

  $("paused").checked = Boolean(status.paused);
  $("paused").disabled = Boolean(status.serverPaused);

  const hosts = status.policy?.exclude_hosts || [];
  $("exclusions").replaceChildren(
    ...(hosts.length ? hosts : ["nothing configured yet"]).map((host) => {
      const item = document.createElement("li");
      item.textContent = host;
      return item;
    }),
  );

  $("api-url").value = status.apiUrl || "";
  $("console-url").value = status.consoleUrl || "";
  $("rig-url").value = status.rigUrl || "";
  // status() no longer carries the token itself -- only whether one is saved.
  $("rig-token").value = "";
  // The token typed here is the tenant's; on save the rig mints one for this
  // browser and that is what stays saved. The tenant's is not kept.
  $("rig-token").placeholder = status.rigRegistered
    ? "registered: this browser holds a token of its own"
    : status.rigTokenSet
      ? "saved: the tenant's token, until a rig that registers browsers is saved"
      : "the tenant's rig token; this browser keeps one of its own";
  $("purge").disabled = !status.deviceId;

}

function trouble(error) {
  $("trouble").textContent = error.message;
}

$("sign-in").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    render(
      await ask({
        kind: "sign-in",
        apiUrl: $("api-url").value.trim(),
        consoleUrl: $("console-url").value.trim(),
        token: $("token").value.trim(),
      }),
    );
    $("token").value = "";
  } catch (error) {
    trouble(error);
  }
});

$("sign-out").addEventListener("click", async () => {
  try {
    await ask({ kind: "sign-out" });
    render(await ask({ kind: "status" }));
  } catch (error) {
    trouble(error);
  }
});

$("paused").addEventListener("change", async (event) => {
  try {
    render(await ask({ kind: "set-paused", paused: event.target.checked }));
  } catch (error) {
    trouble(error);
  }
});

$("rig").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const answer = await ask({
      kind: "rig",
      rigUrl: $("rig-url").value.trim(),
      rigToken: $("rig-token").value.trim(),
    });
    render(answer);
  } catch (error) {
    trouble(error);
  }
});

// Deleting an hour of somebody's work cannot be one stray click, and it cannot
// be a modal either: a dialog raised from an extension page blocks everything
// else this browser is doing, including the worker being asked to do the
// deleting. So the button asks in place, and forgets it was asked after a few
// seconds -- a page left open on "Really?" must not delete an hour tomorrow
// morning when somebody brushes the trackpad.
let armed = null;

$("purge").addEventListener("click", async () => {
  if (!armed) {
    $("purge").textContent = "Really delete the last hour?";
    armed = setTimeout(() => {
      armed = null;
      $("purge").textContent = "Delete the last hour";
    }, 5000);
    return;
  }

  clearTimeout(armed);
  armed = null;
  $("purge").textContent = "Delete the last hour";
  $("purge").disabled = true;
  $("purged").textContent = "deleting…";
  try {
    const gone = await ask({ kind: "purge", hours: 1 });
    // Counted, because "your evidence is deleted" is a promise and a number is
    // what makes it checkable.
    $("purged").textContent =
      `deleted ${gone.events} events in ${gone.batches} batches, ` +
      `and ${gone.artifacts ?? 0} screenshots`;
    render(await ask({ kind: "status" }));
  } catch (error) {
    $("purged").textContent = `nothing was deleted: ${error.message}`;
  } finally {
    $("purge").disabled = false;
  }
});

ask({ kind: "status" }).then(render).catch(trouble);
