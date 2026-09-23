# Notes for `backend/scripts/stub_device.py`

Comments and docstrings moved out of [`backend/scripts/stub_device.py`](../../../../backend/scripts/stub_device.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../backend/scripts/stub_device.py#L1): Docstring

> A browser that isn't.
>
> Holds the command channel open and answers whatever is sent down it, so the
> backend half can be exercised before the extension's own client exists -- and
> afterwards, when the question is whether a failure is ours or Chrome's.
>
>     make token tenant=acme principal=you
>     curl -s -X POST localhost:8000/v1/agents/register       -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json'       -d '{"label":"stub"}'
>     uv run python scripts/stub_device.py       ws://localhost:8000/v1/agents/<device>/commands $TOKEN $DEVICE_SECRET
>
> Every answer is a success, on purpose: what this proves is the path, not the
> page. Pass --refuse to have it answer `control_not_found` instead, which is how
> the escalation policy is exercised without a browser.
>
> Pass --approve and it also presses Approve, **as itself**. That is the one
> check `approver_is_the_driver` exists for and the one thing nothing in this
> repository had ever exercised: every approval ever recorded here was tapped
> with the tenant's bare credential, naming no browser, which is the
> supervisor's-console path and skips the check entirely. A stub holding a
> socket already holds the two things a real panel proves itself with -- the
> `device_id` in the URL it dialled and the `X-Device-Secret` it dialled with --
> so it can send the pair, and the row it leaves names a browser.
>
> What it still is not: a Chrome. The panel's own `rigApprove` is not exercised
> by this, and a warehouse that can show its own write back is what a `held`
> outcome needs. This closes the backend half of steps 8 and 9, not the browser
> half.

## module, [line 12](../../../../backend/scripts/stub_device.py#L12): Note on the line above

Code: `APPROVE_EVERY_S = 1.0`

> How often the approver asks whether anything is parked on a person.
>
> A poll and not a push, because there is no channel for this: the command
> socket carries commands TO a browser, and a parked run sends nothing down it
> -- `run_workflow` is sitting on an `asyncio.Event` and the panel a real
> operator uses polls too. One second against `K_APPROVAL_WAIT_S`, so a run
> parks and is answered well inside its own patience.

## module, [line 14](../../../../backend/scripts/stub_device.py#L14): Note on the line above

Code: `WAS = "https://wms.example/orders"`

> Where this browser that isn't is standing.
>
> `ui.url` used to answer a constant, and a constant is a browser that never goes
> anywhere: the runner navigates, asks where it is, is told the old page, and
> calls the step failed with *the browser is currently on the wrong page*. It
> never got past step 1 of a job whose first step is in the mail. So `navigate`
> moves this, and `ui.url` reads it -- the least a stub can do and still be a
> place.

## `_device_of`, [line 28](../../../../backend/scripts/stub_device.py#L28): Docstring

> The browser this socket is, read off the URL it dialled.
>
> `/v1/agents/<device_id>/commands`. Taken from the URL rather than asked
> for as a flag because these are the same id by construction: a stub that
> could be told a different one is a stub that can approve for a browser it
> is not -- which is the exact thing the check under test refuses, and a
> test rig must not be able to fake the thing it is proving.

## `approve_as_this_browser`, [line 35](../../../../backend/scripts/stub_device.py#L35): Docstring

> Press Approve on this browser's own parked runs, as this browser.
>
> Both halves of the pair or neither: `?device_id=` in the query and
> `X-Device-Secret` in the header. Half of it is `asking_device`'s 404, and
> NEITHER is the console path -- a silent 200 recording an approval by
> nobody, on the door whose whole job is recording who let the write out.
>
> Only this browser's runs are tapped, and the filter is here rather than
> left to the 403. The queue is the tenant's: `?awaiting=true` answers with
> every parked run of every browser, deliberately, so that a supervisor can
> clear any of them. A stub that tapped all of them would be answering for
> windows it is not driving, get `NotDrivingThisRun` for its trouble, and
> bury the one answer that matters in 403s.

## `_both`, [line 119](../../../../backend/scripts/stub_device.py#L119): Docstring

> The socket, and optionally the approver beside it.
>
> The socket is the one that decides when this process is done: a stub whose
> command channel closed has stopped being a browser, and an approver still
> polling for a browser that is gone would answer for a run nothing is
> driving. So the poller is cancelled with it rather than waited on.

## module, [line 19](../../../../backend/scripts/stub_device.py#L19): Comment

Code: `"navigate": {"navigated": True},`

> The runner's other leaf. A step whose plan is `navigate` got
> `unsupported: navigate` from here and failed the whole run at step 1,
> because this map was written before `plan_step` learnt to move the tab
> itself. `commands.js:511` is what a real browser answers.

## `approve_as_this_browser`, [line 50](../../../../backend/scripts/stub_device.py#L50): Comment

Code: `print(f"!! could not read the queue: {problem}")`

> The API restarting under a stub that outlives it is the
> ordinary case, not an error worth dying of: a poller that
> exits on the first refused connection takes the socket with
> it and the run it was going to answer parks out its wait.

## `approve_as_this_browser`, [line 57](../../../../backend/scripts/stub_device.py#L57): Comment

Code: `answered.add(run_id)`

> Recorded before the call, not after. A tap that reaches the
> backend and then fails to answer -- a dropped socket, a
> timeout -- has still let the write out, and a retry would
> tap a second time on a run that parked again for a different
> reason.

## `serve`, [line 70](../../../../backend/scripts/stub_device.py#L70): Comment

Code: `async with websockets.connect(url, subprotocols=["bearer", token, secret]) as socket:  # t`

> Three protocols, not two. The socket stopped taking a tenant bearer alone
> when `commands` began reading `protocols[2]` as the device secret: a valid
> credential is not ownership, and a socket that let one stand in for the
> other would hand any of a tenant's tokens the command channel of any of
> its browsers. Called with two, the handshake is refused with a 403 that
> says nothing -- deliberately, so a wrong secret and an absent device
> close the same way.

## `serve`, [line 88](../../../../backend/scripts/stub_device.py#L88): Comment

Code: `answer = {`

> Refused, not faked. `look()` reads a refusal as "no picture"
> and plans from the url and the digest, which is exactly the
> degraded path a real browser takes when the page to be driven
> is not the visible one. A fabricated PNG would instead send
> the model a picture of nothing and invite it to click in it.
