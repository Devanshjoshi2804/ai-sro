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

  // Prefilled from the build's own deployment, so a person signing in has one
  // thing to do and it is the one thing that is theirs. `status` carries what
  // this browser already stored; before it has stored anything those are the
  // generated defaults, which is the case this exists for.
  $("api-url").value = status.apiUrl || "";
  $("console-url").value = status.consoleUrl || "";
  // Opened only when there is nothing to sign in with and the addresses are
  // therefore worth a glance. Once connected they are noise.
  $("addresses").open = !status.deviceId && !status.apiUrl;
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
