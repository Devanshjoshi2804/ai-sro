# Notes for `backend/src/sro/application/skill/adopt_rig_workflow.py`

Comments and docstrings moved out of [`backend/src/sro/application/skill/adopt_rig_workflow.py`](../../../../../../../backend/src/sro/application/skill/adopt_rig_workflow.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/skill/adopt_rig_workflow.py#L1): Docstring

> A workflow the rig mined, adopted into the skill library.
>
> `version_from_rig` builds a `SkillVersion` and stops, because a `Skill` needs
> an `ObjectiveKey` -- objective type, target system, entity type, facility,
> direction -- and the rig produces none of those. It knows a title, the systems
> a job touched and a shape key. Deriving "an inbound receipt against BLR1" from
> `Create Work Area NEWTESTS` would be a guess wearing the clothes of a finding.
>
> So this is the seam where a person joins in, and the whole design of the module
> is about keeping the two contributions distinguishable afterwards:
>
> - **The rig produced the version.** `induced_by` is the rig, not the person who
>   adopted it. `Provenance.induced_by` says "who produced this version", and its
>   own docstring makes the point that `drift-repair` goes there where the system
>   did the work and "does not pretend to be" a person. A model reading 170 hours
>   of capture is the same kind of author.
> - **A person chose to adopt it, and named what it is for.** That is a decision
>   with somebody's name on it, so it goes in the note where a reviewer reads it.
>
> Nothing arrives promoted. `add_version` refuses anything but RECORDED, and that
> is the right refusal: the objective is a person's reading of a title, and the
> steps are a model's reading of a day. Neither has been checked against the
> other by anybody.
>
> Nothing here reaches for the rig either. The evidence arrives as the shape
> `GET /v1/workflows/{id}/evidence` serves, from whatever fetched it -- so the
> two systems share a shape rather than a dependency, and a caller can adopt a
> workflow out of a file as easily as out of a running rig.

## module, [line 15](../../../../../../../backend/src/sro/application/skill/adopt_rig_workflow.py#L15): Note on the line above

Code: `RIG = PrincipalId("rig")`

> The author of these steps. A model reading a day of capture is not a person
> and does not pretend to be one -- the same reasoning `drift-repair` carries.

## `Adopted`, [line 22](../../../../../../../backend/src/sro/application/skill/adopt_rig_workflow.py#L22): Note on the line above

Code: `created_the_skill: bool`

> False where this is a second reading of a job the library already knew.
> A reviewer comparing two versions of one objective is the point of saying
> so: the rig watching the same job twice is evidence, not a duplicate.

## `_title`, [line 78](../../../../../../../backend/src/sro/application/skill/adopt_rig_workflow.py#L78): Docstring

> The workflow's own title, where it has a usable one.
>
> `str()` of whatever was there put `{'a': 1}` in a library as a skill name.
> A title is a string or it is nothing, and the objective's slug is a better
> fallback than a rendered dict.

## `_adopted_by`, [line 83](../../../../../../../backend/src/sro/application/skill/adopt_rig_workflow.py#L83): Docstring

> The provenance, with who adopted it and under what name appended.
>
> A sentence rather than a field, because "who pressed adopt" is not a
> question any screen filters a library by -- unlike "was this written by a
> person or by the system", which has `induced_by` and `repaired_from`
> already. What it must not do is go unrecorded: the objective is the one
> part of this version nobody derived from evidence.

## `AdoptRigWorkflow.execute`, [line 31](../../../../../../../backend/src/sro/application/skill/adopt_rig_workflow.py#L31): Docstring

> Adopt one mined workflow under an objective a person has named.
>
> The facility comes from the objective rather than from a second
> argument. A credential reference is a vault key scoped per system and
> facility, and the objective is the only place this system records which
> facility a job belongs to -- taking it separately would let a caller
> file a Bengaluru job's credentials under Singapore by passing two
> arguments that disagree.

## `AdoptRigWorkflow.execute`, [line 51](../../../../../../../backend/src/sro/application/skill/adopt_rig_workflow.py#L51): Comment

Code: `version=skill.next_version_number() if skill else 1,`

> Sequential and append-only. A second reading of a job the
> library already knows is v2, never a replacement: existing
> versions are what runs are judged against.

## `AdoptRigWorkflow.execute`, [line 60](../../../../../../../backend/src/sro/application/skill/adopt_rig_workflow.py#L60): Comment

Code: `version.provenance = _adopted_by(version, ctx.principal_id, objective)`

> Everything the person contributed, where a reviewer looking at the
> version reads it. `induced_by` is the rig because the rig wrote
> the steps; this is the other half.
