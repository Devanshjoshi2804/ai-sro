"""Whether a sentence is asking for something to be DONE or to be FOUND OUT.

One box, two worlds behind it. `read_chat` resolves a sentence against the
jobs an operator was seen doing; `plan_lookups` resolves one against what the
systems know. Sending a question to the first produces "no job matched" and
sending an instruction to the second produces a plan to read a page nobody
asked about, so something has to decide, and the deciding is here rather than
in the extension for the reason every rule in this codebase lives on one side
of the wire: `shape_of` served a shape `recognise.js` could never match for
weeks because each side was only ever read against itself.

**No model.** A model call to decide which model call to make doubles the
latency of every sentence somebody types to answer a question whose evidence
is the first word. This is a word rule, it is wrong sometimes, and the cost of
being wrong is bounded in both directions: a question read as a job is
answered "no job matched" and a job read as a question comes back with a plan
and no press. Neither writes anything.

**A job verb wins over a question mark.** "Can you add demo values?" is an
instruction with a polite shape, and reading it as a question is the failure
that matters: the operator waits for something to happen and nothing does.

**What is left over is a job.** Not because most sentences are jobs, but
because a lookup drives the browser on its own -- it opens tabs and reads
pages -- and a job stops at an offer somebody has to press. When the rule
cannot tell, the path that waits for a person is the one to take.
"""

from __future__ import annotations

DOING = frozenset(
    {
        "create",
        "add",
        "make",
        "new",
        "update",
        "change",
        "edit",
        "set",
        "delete",
        "remove",
        "cancel",
        "assign",
        "upload",
        "import",
        "export",
        "start",
        "run",
        "send",
        "submit",
        "approve",
        "release",
        "print",
        "close",
        "confirm",
        "fix",
        "do",
    }
)
"""Verbs that ask for the world to change. First word only: "update" in "which
suppliers were updated today" is a tense, not an instruction, and a rule
reading it anywhere would send every question about changed records to the
miner."""

ASKING = frozenset(
    {
        "what",
        "which",
        "where",
        "when",
        "who",
        "whose",
        "why",
        "how",
        "is",
        "are",
        "was",
        "were",
        "does",
        "do",
        "did",
        "can",
        "has",
        "have",
        "any",
    }
)
"""First words that open a question."""

LOOKING = frozenset(
    {
        "find",
        "search",
        "look",
        "check",
        "show",
        "list",
        "get",
        "fetch",
        "tell",
        "status",
        "count",
    }
)
"""First words that ask to be told something. `get` and `fetch` sit here
rather than in `DOING` on purpose: they are the words an operator uses for a
read, and the HTTP verb they share a name with is the read one."""


def is_a_question(said: str) -> bool:
    """Whether this sentence wants an answer rather than an action."""
    words = [word.strip(",.?!\"'()[]:;").lower() for word in said.split()]
    words = [word for word in words if word]
    if not words:
        return False

    first = words[0]
    if first in DOING:
        return False
    # "please check the supplier list", "could you find out how many" -- the
    # courtesy is not the sentence, so it is stepped over before the rule runs.
    if first in ("please", "could", "would", "can", "pls", "plz", "hey", "ok") and len(words) > 1:
        rest = (
            words[1] if words[1] not in ("you", "we", "i") else (words[2] if len(words) > 2 else "")
        )
        if rest in DOING:
            return False
        if rest in LOOKING or rest in ASKING:
            return True
    if first in ASKING or first in LOOKING:
        return True
    return said.rstrip().endswith("?")
