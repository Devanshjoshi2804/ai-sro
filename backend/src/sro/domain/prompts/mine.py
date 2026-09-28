from __future__ import annotations

from sro.domain.prompts.record import EdgeCase, Prompt

_ROLE = "You are reading a stretch of one warehouse operator's working day."

_TASK = """\
Each entry below is one thing they did in a browser: the control they touched,
the calls it caused, and a short reading of it made earlier.

Find the jobs. A job is a run of doings that together accomplish one thing a
person would name -- creating a supplier, receiving a shipment, correcting a
count. A job may span more than one system: the operator may do half of it in a
warehouse system and half in an ERP, and those halves are still one job.

Some of what you are reading may be another doing of a job listed under
"Jobs already proven". That list is there so you can RECOGNISE work, not so
you can skip it: report a job you have seen before exactly like any other,
with its steps and its citations. A second doing is the only way anything here
learns which of a job's values vary, and a doing left out is a doing nobody
can learn from. Deciding which of your answers describe the same job is not
your work -- report what you see and it will be worked out.

An operator often does the same job several times in a row -- four customer
types, one after another, from four emails. That is ONE job done four times.
It is not four jobs, and it is not one job of four times the length: report it
once, with the steps of a SINGLE doing, and put what changed between the
doings in `parameters` -- the name of the field, and every value you saw in
it. The steps say what is always done; the parameters say what varies.

A job has something to show for it -- something the operator could point at
afterwards and say that is what I did. Looking something up is a STEP of a job
and not a job: somebody who searches for the record they just created is
finishing one, and somebody who types a query into their own mailbox and reads
what comes back has not started one. A stretch that only looked at things goes
under `unplaced`.

Name the job, not the one doing of it you are reading. The title is what every
doing of that job has in common, so keep the particular values this operator
typed -- codes, names, quantities -- out of it: "Create a Customer Type", never
"Create Customer Type DSS". Those values belong in the steps.

For every step of every job, cite the ids of the gestures that prove it. Cite
before you describe. A step you cannot cite is a step you should not report.

List anything you could not place under `unplaced`, once, at the top level
beside `workflows`. It is what is left of the WINDOW when every job in it has
been described -- not something belonging to any one job you found. Do not
force it into a job.

Do not invent a system that the evidence you cited does not touch."""

MINE = Prompt(
    name="mine",
    version=4,
    model="gemini-3.8-flash",
    fallback_model="gemini-3.7-flash",
    thinking="medium",
    role=_ROLE,
    task=_TASK,
    input_contract=(
        "Four untrusted blocks. `day` is the window's gestures as JSON. `crossings` is "
        '"Values appearing in more than one system": each value, with the gestures it was '
        "seen on. `known` is the list the task calls Jobs already proven. `knowledge` is "
        '"What is known about these systems". In `day`, a gesture\'s `tab` is the browser tab '
        "it acted in, and `opened` lists each tab it opened with the tab that opened it "
        '(`{"tab": 9, "from": 7}`): work that carries on in a tab the job opened is still '
        "the same job."
    ),
    output_schema={
        "type": "object",
        "properties": {
            "workflows": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "narrative": {"type": "string"},
                        "systems": {"type": "array", "items": {"type": "string"}},
                        "steps": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "order": {"type": "integer"},
                                    "cites": {"type": "array", "items": {"type": "string"}},
                                    "says": {"type": "string"},
                                    "system": {"type": "string"},
                                    "parameters": {"type": "array", "items": {"type": "string"}},
                                },
                                "required": ["order", "cites", "says"],
                            },
                        },
                        "parameters": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "the field that varies",
                                    },
                                    "seen_values": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "every value observed in it",
                                    },
                                },
                                "required": ["name", "seen_values"],
                            },
                        },
                    },
                    "required": ["title", "steps"],
                },
            },
            "unplaced": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["workflows"],
    },
    unit="workflows",
    edge_cases=(
        EdgeCase(
            "four customer types created one after another from four emails",
            "one job, with `parameters` holding the four codes",
        ),
        EdgeCase(
            "a search typed into the mailbox and its results read",
            "no job; the stretch goes under `unplaced`",
        ),
        EdgeCase(
            "a doing of a job listed under Jobs already proven",
            "reported again, with its steps and its cites",
        ),
    ),
)
