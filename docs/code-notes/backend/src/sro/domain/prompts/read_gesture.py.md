# Notes for `backend/src/sro/domain/prompts/read_gesture.py`

Comments and docstrings moved out of [`backend/src/sro/domain/prompts/read_gesture.py`](../../../../../../../backend/src/sro/domain/prompts/read_gesture.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 25](../../../../../../../backend/src/sro/domain/prompts/read_gesture.py#L25): Note on the line above

Code: `model="gemini-3.8-flash",`

> What reads one gesture into an intent -- `sro.domain.observation.
> reading`, called once per gesture, hundreds a day. The rig's own
> `intent_model` (`new_agent_arch/src/rig/config.py:19`); it was the setting
> `gemini_read_model` until the prompts became records, renamed there
> because `gemini_intent_model` in `config.py` then named an
> unrelated door -- reading one sentence out of a chat message, not one
> gesture out of a browser.
>
> A real bake-off against gemini-3.1-flash-lite and gemini-3.1-pro-preview,
> on real captured gestures, measured this one paying $0.0024/gesture at
> ~4.1s against flash-lite's $0.0003/gesture at ~1.2s and pro-preview's
> $0.0140/gesture at ~11.5s -- and, checked against ground truth rather than
> against each other, this one and pro-preview read the real DOM identifiers
> correctly while flash-lite drifted onto the wrong screen entirely once its
> own wrong reading entered its tail. Pro-preview bought nothing over this
> one on the same evidence. Worth re-running once `with_recent_values` and
> the thin-gesture picture are live in production: both were missing when
> that bake-off ran.

## module, [line 33](../../../../../../../backend/src/sro/domain/prompts/read_gesture.py#L33): Comment

Code: `"properties": {`

> `why` first, and `confidence` last, because a structured answer is
> written left to right: the model fills these fields in this order, so
> this order is the order it thinks in. Asked for `act` first, it commits
> to a verb and then writes the sentence that defends it; asked for `why`
> first, it has to name the evidence -- the label, the component metadata,
> the request body, the picture -- before it names the act, and states a
> confidence with both already written down. The task asks for exactly
> this sequence, and a prompt that asks for one order while the schema
> imposes another is a prompt arguing with itself.

## module, [line 48](../../../../../../../backend/src/sro/domain/prompts/read_gesture.py#L48): Comment

Code: `"propertyOrdering": [`

> Stated rather than left to the key order above. Gemini honours the dict's
> own order today -- measured, both with and without this field -- and
> `propertyOrdering` is the documented way to say so, which makes the
> ordering a promise of the schema rather than an accident of how Python
> happens to preserve insertion order through the SDK's conversion.
