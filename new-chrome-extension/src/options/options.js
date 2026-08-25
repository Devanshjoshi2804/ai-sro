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
    ? "Observing this browser."
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

  $("api-url").value = status.apiUrl || "";
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

ask({ kind: "status" }).then(render).catch(trouble);
