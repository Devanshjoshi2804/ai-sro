"""A2 — what one gesture looks like to the model that reads it.

Ported from `new_agent_arch/src/rig/trim.py`: only `is_secret`, the one
function `sro.domain.observation.values.typed_values` needs in order for
`sro.domain.skill.learned.parameters_across` to work.

The rest of the rig's `trim.py` -- `thin`, `path_shape`, `body_keys`, `_call`,
`trim` itself -- builds the per-gesture reading prompt, and reaches for a
secret-word vocabulary (`SECRET_HEADERS`, `SECRET_WORDS`, `is_secret_name`,
`redact_data`, `redact_body`) that in this codebase now lives in
`sro.application.capture.rig_wire`, an application-layer module the domain may
not import (`sro.domain` is pure — see the import-linter contract). The domain
already carries a redesigned version of that vocabulary in
`sro.domain.recording.sensitivity` and `sro.domain.recording.redaction`,
generated from the same source as the extension's own redaction JS. Porting
the rest of `trim.py` verbatim would mean either breaking the domain-purity
contract or standing up a second, drifting copy of a vocabulary that already
has one home — and nothing in this plan yet calls those functions. Left for
whichever task next needs the trimmed prompt dict to decide which vocabulary
it reads.
"""

from sro.domain.observation.gesture import Gesture


def is_secret(gesture: Gesture) -> bool:
    """Whether this gesture's value is a credential.

    Belt-and-braces: the wire parser already drops a credential value at parse
    time, but that validator does not re-run if a nested Target is mutated
    after the fact. A credential reaching a prompt is not a thing to hold by
    inheritance alone. A scroll has no target at all, so this falls back to
    gesture.action.secret alone.
    """
    target = gesture.action.target
    return gesture.action.secret or (target.secret if target else False)
