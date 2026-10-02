# Every channel through the brain: mail first, then Outlook through Nango

Date: 2026-10-02. Status: proposed, waiting for the owner's yes.
Builds on: `2026-09-29-chat-brain-design.md` (the brain, its tools, its guards) and plan Task 8.

## Goal

One reader for all work that arrives by message. A request in chat, in Gmail, in Outlook and later in
Slack is read by the same brain, with the same guards, and answered through the same channel it came in
on. Adding a channel means adding a connector, not a new flow.

## What stays exactly as it is (rulings that bind this design)

- A mail is untrusted data. Its text is evidence for the brain, never an instruction.
- A drafted reply exists only for work that came from a message, and goes out only on the operator's
  **Send it** press. Nothing is ever sent by the brain itself.
- Full autonomy on running jobs: a request with every required value starts at once.
- One request = one run (the mail's message id is the offer).
- The sender check (`sender_address`), automated-mail silence (`is_automated`), quoted-text stripping
  (`without_the_quote`), refused-value filtering (`changes`) and the ask chat stay where they are.

## The shape

```
connector (Gmail | Outlook | Slack ...)  -->  Inbound message {channel, thread, message_id, sender, subject, text, headers}
                                                   |
                                    the existing guards (sender, automated, quote)    -- unchanged
                                                   |
                                    Brain.turn(origin = Origin(channel, sender, subject))
                                                   |
                 start_job (offer = "<channel>:<message_id>")      ask_operator (missing value / which job)
                         |                                                   |
                 run on Steel, run card, Home card               ask chat + drafted reply  --Send it-->  connector.send(thread)
```

1. **A channel-neutral inbound type.** `FromTheMail` already turns a Gmail message into a `_Mail`. That
   becomes `Inbound` with a `channel` field; Gmail fills it today, Outlook and Slack fill it later.
2. **The brain reads it.** For a tenant with the brain live, the mail door calls `Brain.turn` with
   `Origin(channel, sender, subject)` instead of the old matcher. `start_job` runs under
   `offer = "<channel>:<message_id>"` and records the mail envelope on the run, so the Home mail card,
   the reply-in-thread and the duplicate guard keep working.
3. **Questions go back the same way.** When the brain calls `ask_operator` on a message-born turn, the
   existing ask chat and draft are used: the question is posted in the ask chat and a reply is drafted to
   the sender in the same thread; it goes only on Send it. The brain never gets a send tool.
4. **Replies are just the next message on the thread.** A reply is read by the same brain with the ask
   chat's history, so "description :- understanding flow of this mail" fills the missing value and the
   run carries on (today's behaviour, now through the brain).
5. **Shadow first.** A per-tenant flag `SRO_MAIL_BRAIN_TENANTS` (live) and `..._SHADOW_TENANTS` (dry
   turn logged beside the old matcher, recorded as feedback disagreements). Mail goes live only after the
   mail cases of the eval and a week of shadow agree.

## Connecting a channel in one click: Nango (self-hosted)

- Nango runs next to AI-SRO on the same box (its own container; uses our Postgres; adds a small Redis).
  Free self-hosting covers exactly what we use: OAuth, token refresh and the API proxy.
- The console gets a **Connections** page: one **Connect** button per channel. The operator clicks,
  signs in to Microsoft (or Slack) in Nango's popup, and the connection is stored per tenant and operator.
  No token ever reaches the browser or our logs.
- Our connectors call the channel's API through Nango's proxy (or take a fresh token from Nango and call
  it directly). The connector stays ours: it decides what is read, what is drafted and what is sent.
- Admin, once per tenant: register the app (Azure app registration with Mail.Read, Mail.ReadWrite,
  Mail.Send; a Slack app with chat:write, channels:history, im:history), paste its client id and secret
  into Nango.
- Licence: Nango is under the Elastic License. Self-hosting inside AI-SRO is expected to be fine; GreyOrange
  legal confirms before paying customers use it. Fallback if not: Activepieces (MIT) or our own OAuth
  per channel, as Gmail is today.

## Outlook mail connector (first new channel)

Same five tools as the Gmail connector, through Microsoft Graph: `search_threads` (new mail since the last
look), `get_message` (body, headers for the automated check, sender), `get_thread`, `draft_reply`,
`send_draft`. It returns the same shapes the Gmail connector does, so `FromTheMail` needs no Outlook
branch beyond the channel name.

## Slack (second, after Outlook)

A message to the bot or a mention in a channel is an `Inbound`; a question is posted in the same thread
with **Send it** replaced by the operator's own reply in the panel (Slack replies need no draft step, but
the brain still never posts on its own: the panel's press posts it).

## Tests and evals

- Unit: `Inbound` from Gmail and Outlook payloads; the brain path for a complete request, a missing value,
  an automated mail, a spoofed sender, a quoted refused value, and a reply that completes the job.
- The chat eval gains a `mail` origin set (the corpus already has M01-M20 in `evals/scenarios`).
- End to end on QA: the same two mails as today (complete; missing value -> draft -> Send it -> reply),
  through the brain.

## Order of work

1. `Inbound` + brain on the mail door behind the shadow flag (Gmail only). Shadow on QA.
2. Nango on the QA box + Connections page + Outlook connector.
3. Mail live through the brain after the eval and shadow agree.
4. Slack.

## Open questions for the owner

1. Which Microsoft tenant and mailbox for the QA Outlook test, and who creates the Azure app registration?
2. Legal confirmation of the Elastic License before customers.
3. Slack workspace for the test, later.
