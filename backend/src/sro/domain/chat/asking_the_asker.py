from __future__ import annotations

from sro.domain.chat.asking import Pending, shortened

K_RE = "Re: "


def draft_for(pending: Pending, *, about: str = "", signed: str = "") -> tuple[str, str]:
    subject = f"{K_RE}{about}" if about.strip() else f"{pending.title} — one thing missing"

    wanted = pending.asking_for
    holds = pending.limits.get(wanted)
    lines = [
        f"I am working on {pending.title} from your request"
        + (f" ({about})." if about.strip() else "."),
        "",
    ]

    held = [
        f"  {name}: {shortened(value)}"
        for name, value in pending.values.items()
        if name not in pending.missing and value.strip()
    ]
    if held:
        lines += ["What I have so far:", *held, ""]

    had = pending.values.get(wanted, "")
    if why := pending.refused.get(wanted):
        lines.append(
            f"{wanted}{f' {shortened(had)}' if had.strip() else ''} could not be used:"
            f" {shortened(why).rstrip('.')}."
            f" What should {wanted} be instead?"
        )
    elif holds is not None and had.strip():
        lines.append(
            f"{wanted} needs to be {holds} characters or fewer. The request said"
            f" {shortened(had)}, which is {len(had)}."
        )
    elif holds is not None:
        lines.append(f"I still need {wanted}. It needs to be {holds} characters or fewer.")
    else:
        lines.append(f"I still need {wanted}, and I could not find it in the thread.")

    rest = list(pending.missing[1:])
    if rest:
        lines.append(f"(I will need {', '.join(rest)} after that.)")

    lines += ["", "Reply to this mail and I will carry on from here."]
    if signed.strip():
        lines += ["", f"Sent for {signed.strip()} by AI-SRO."]
    return subject[:K_SUBJECT], "\n".join(lines)


K_SUBJECT = 200


def worth_asking(pending: Pending) -> bool:
    return bool(pending.missing and pending.workflow_id)


__all__ = ["draft_for", "worth_asking"]
