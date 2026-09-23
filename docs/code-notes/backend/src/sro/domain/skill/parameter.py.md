# Notes for `backend/src/sro/domain/skill/parameter.py`

Comments and docstrings moved out of [`backend/src/sro/domain/skill/parameter.py`](../../../../../../../backend/src/sro/domain/skill/parameter.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/skill/parameter.py#L1): Docstring

> Skill parameters. See docs/07-adr/004-diff-parameterisation.md.

## module, [line 12](../../../../../../../backend/src/sro/domain/skill/parameter.py#L12): Note on the line above

Code: `_BREAKS_THE_LINE = re.compile(r"[\x00-\x1f]")`

> What no slot but a whole body can carry.
>
> A quote and a backslash are no longer here: a value going into a body is
> escaped on its way in, and one going into a URL or a header adds no structure
> by carrying either. A control character does: a `\r` ends a header value and
> begins whatever follows it as a second header, and a URL has no way to spell
> one at all. A body leaf could escape it -- `json.dumps` does -- and is refused
> along with the rest, because nothing on a `Parameter` separates the leaf from
> the header, and no form control an operator fills in produces one anyway.

## `_not_json`, [line 15](../../../../../../../backend/src/sro/domain/skill/parameter.py#L15): Docstring

> Refuse `NaN`, `Infinity` and `-Infinity`.
>
> Python's `json` reads them and writes them; JSON has no such literals, and
> neither does anything on the other end of the wire. Into a bare slot they
> would go out unquoted -- `{"qty":NaN}` -- and a WMS that parses strictly
> rejects the whole write, while one that does not stores a quantity nobody
> can read back.

## `json_type_of`, [line 19](../../../../../../../backend/src/sro/domain/skill/parameter.py#L19): Docstring

> What JSON calls this Python value: the vocabulary both the diff and the
> renderer use to say what a slot holds. `bool` before `int`, because in
> Python a boolean is one.

## `ParameterKind`, [line 34](../../../../../../../backend/src/sro/domain/skill/parameter.py#L34): Note on the line above

Code: `INPUT = "input"`

> Supplied by whoever runs the skill.

## `ParameterKind`, [line 36](../../../../../../../backend/src/sro/domain/skill/parameter.py#L36): Note on the line above

Code: `DERIVED = "derived"`

> Produced by an earlier step's response. Never prompted for.

## `ParameterKind`, [line 38](../../../../../../../backend/src/sro/domain/skill/parameter.py#L38): Note on the line above

Code: `ITERATED = "iterated"`

> A field of the thing a loop is acting on this time round.
>
> Never prompted for and never read straight out of a response either: the
> value is whichever element of the list the loop is on, so it exists only
> inside the loop's body and only once the list has arrived.

## `Evidence`, [line 41](../../../../../../../backend/src/sro/domain/skill/parameter.py#L41): Docstring

> How firmly we know this is a parameter rather than a constant.

## `Evidence`, [line 42](../../../../../../../backend/src/sro/domain/skill/parameter.py#L42): Note on the line above

Code: `PROVEN = "proven"`

> Two demonstrations disagreed here. A fact, not a reading.

## `Evidence`, [line 44](../../../../../../../backend/src/sro/domain/skill/parameter.py#L44): Note on the line above

Code: `PROPOSED = "proposed"`

> One demonstration, and a model's reading of it. One value is just a
> value: nothing about a single run distinguishes the LPN the operator chose
> from the site code that is the same every time. Proposed parameters are
> shown as such, are confirmed by whoever runs the skill, and become proven
> the first time a second demonstration disagrees with the first.

## `Parameter`, [line 52](../../../../../../../backend/src/sro/domain/skill/parameter.py#L52): Note on the line above

Code: `observed_values: tuple[str, ...] = ()`

> The values that proved this field varies -- evidence for the reviewer.

## `Parameter`, [line 59](../../../../../../../backend/src/sro/domain/skill/parameter.py#L59): Note on the line above

Code: `transform: Transform | None = None`

> What was done to the value between the response and the call that sent it.
>
> Absent for the ordinary case, where it was handed over unchanged. Present
> where two demonstrations agreed on a reformatting -- `42` answered, `LPN-00042`
> sent -- which is the shape of most work that crosses two systems.

## `Parameter`, [line 61](../../../../../../../backend/src/sro/domain/skill/parameter.py#L61): Note on the line above

Code: `options: Options | None = None`

> Where this value can be chosen from, where the screen chose it.
>
> A parameter with options is a dropdown, not a text box: the console fetches
> them from the system itself when it draws the field, so the operator picks a
> supplier's address the way they would have on the screen instead of
> reciting an id.

## `Parameter`, [line 63](../../../../../../../backend/src/sro/domain/skill/parameter.py#L63): Note on the line above

Code: `absent_as: str | None = None`

> What to send when nobody supplies it, exactly as the demonstration that
> skipped it sent -- `"null"` for a number the form nulls, `""` for a text
> control it empties. Never chosen here: a form that wants one and gets the
> other rejects the write.

## `Parameter`, [line 65](../../../../../../../backend/src/sro/domain/skill/parameter.py#L65): Note on the line above

Code: `unquoted_as: str | None = None`

> The JSON type the body slot holds, where the template leaves that slot
> without quotes round it -- `"number"`, `"boolean"`, `"string"`.
>
> Two separate facts decide the two halves of this. Whether the slot can be
> quoted is decided by the absent form: a quoted slot renders `"null"`, the
> four characters, where the demonstration sent a JSON `null`. What a
> supplied value has to be is decided by the type the other demonstration
> actually filled -- and those disagree in both directions. A form that
> nulls an untouched *text* box gives a text field an unquoted slot, and a
> value going in there is JSON-encoded rather than pasted in raw; a number
> field whose form empties to `""` keeps its quotes, and its slot renders
> the empty string the demonstration sent.
>
> `None` where every site this parameter fills is quoted, which is every
> required field: nothing has shown what such a field's absence looks like,
> so its slot keeps the quotes the recorded body had.

## `Parameter`, [line 67](../../../../../../../backend/src/sro/domain/skill/parameter.py#L67): Note on the line above

Code: `is_the_body: bool = False`

> Whether this value *is* a request body rather than a value inside one.
>
> A body that is not JSON -- SOAP, XML, form-encoded -- is parameterised
> whole: the template is the placeholder and nothing else. That is the one
> destination where escaping is wrong rather than harmless, because there is
> no surrounding string to escape into, and the one where refusing a `"` is
> fatal rather than annoying: an XML body carries quotes on every single run,
> so the rule that kept a value from ending its own JSON string made such a
> task permanently unrunnable.
>
> False, meaning "escape it", for everything else and for everything stored
> before this field existed. Which is the safe default in both directions: a
> value that needs no escaping is unchanged by it, and a value that does is
> the one this exists to stop writing the rest of the body.

## `Parameter.optional`, [line 70](../../../../../../../backend/src/sro/domain/skill/parameter.py#L70): Docstring

> Whether a run may leave this out.
>
> Derived rather than stored, because it is not a second fact: what makes
> a field optional is one demonstration having left it alone, and
> `absent_as` is what that demonstration sent instead. Held separately,
> the two disagreed -- a parameter could be built with an absent form and
> `optional=False`, and the two sides of the system asked different
> questions about it. Emission read the absent form and unquoted the
> slot; execution read the flag and never filled it, and the write went
> out as `{"deltaPriority":}`.
>
> Proved, not assumed, either way: a field filled in every demonstration
> there is stays required, because nothing has shown the task works
> without it.

## `Parameter.absent_value`, [line 74](../../../../../../../backend/src/sro/domain/skill/parameter.py#L74): Docstring

> What goes in the slot when nobody supplies a value.
>
> The absent form as it is *substituted*, which is not the JSON it is
> stored as wherever the slot keeps its quotes: a text control the form
> empties wants the empty string in there, not the two characters `""`.
>
> One definition, asked by both the side that fills the slot and the
> side that decides what may go in it. Held apart, they disagreed: two
> quote characters supplied as a value were accepted as "the form the
> demonstration sent", substituted as text into a slot that already had
> quotes round it, and the write went out with four of them in a row.

## `Parameter.rejects`, [line 80](../../../../../../../backend/src/sro/domain/skill/parameter.py#L80): Docstring

> Why this value cannot be put in this parameter's slot, or ``None``.
>
> Two rules, because only two things a value can carry cannot be dealt
> with by encoding it. A quoted slot used to be the third: a value
> carrying a `"` ended its own string, so it was turned away. It is
> escaped on the way in now, exactly as an unquoted string slot has
> always been -- same destination, same kind of value -- and the cost of
> refusing was real. A whole-body parameter carries quotes on every run.
>
> What is left. A bare slot renders its value as JSON with no quotes
> round it, so `2,"approved":true` in a quantity writes a field nobody
> demonstrated straight into a live warehouse: the value has to be the
> type the demonstration proved that slot holds, and no amount of
> escaping makes it one. And a control character is refused wherever the
> value is not itself the body, because the same value is substituted as
> text into headers and URLs, neither of which can carry one.
>
> Said as a sentence rather than a boolean because the answer is shown
> to whoever supplied the value, and "no" on its own is not something
> anybody can act on.

## `Parameter.rejects`, [line 82](../../../../../../../backend/src/sro/domain/skill/parameter.py#L82): Comment

Code: `return None`

> The form the demonstration itself sent, put here by execution
> when nobody supplied a value. It is JSON by construction.

## `Parameter.rejects`, [line 84](../../../../../../../backend/src/sro/domain/skill/parameter.py#L84): Comment

Code: `return None`

> The value is the body. There is nothing round it to write more
> of, and nothing to escape it into.

## `Parameter.rejects`, [line 92](../../../../../../../backend/src/sro/domain/skill/parameter.py#L92): Comment

Code: `pass`

> Encoded on its way into the body, quotes and all, so there is
> nothing here a value can end.
