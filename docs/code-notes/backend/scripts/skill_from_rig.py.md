# Notes for `backend/scripts/skill_from_rig.py`

Comments and docstrings moved out of [`backend/scripts/skill_from_rig.py`](../../../../backend/scripts/skill_from_rig.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../backend/scripts/skill_from_rig.py#L1): Docstring

> A workflow the rig mined, fetched over HTTP and built into a version.
>
> The three bridge modules -- `from_rig`, `network_from_rig`, `version_from_rig`
> -- turn a mined workflow into a `SkillVersion`. This is the proof that they can
> be reached without the rig's database file, which is the whole point of
> `GET /v1/workflows/{id}/evidence` existing: nothing here imports `rig`, and
> nothing here opens a SQLite store.
>
> Without `--adopt` it stops at the version and prints what a person would be
> naming. A `Skill` needs an `ObjectiveKey` -- objective type, target system,
> entity type, facility, direction -- and the rig produces none of those.
> Deriving "an inbound receipt against BLR1" from `Create Work Area NEWTESTS`
> would be a guess wearing the clothes of a finding. Naming what a job is FOR is
> a person's, so it is typed rather than inferred, one workflow at a time.
>
>     # what is there, and what a person would be naming
>     uv run python scripts/skill_from_rig.py --rig http://127.0.0.1:8099         --token "$RIG_INGEST_TOKEN" --facility SG
>
>     # adopt one, under a name somebody chose
>     uv run python scripts/skill_from_rig.py --rig ... --token ...         --workflow wfl_abc --adopt         --objective create_work_area --entity work_area         --system blue_yonder --facility SG --direction inbound

## `Unreachable`, [line 20](../../../../backend/scripts/skill_from_rig.py#L20): Docstring

> The rig did not answer, or answered something this cannot use.
>
> Its own class so a caller can say WHICH request failed. A bare HTTPError
> escaping as a traceback is the wrong report for the commonest case by far:
> a rig started before the evidence route existed answers `/v1/workflows`
> with a 200 and `/v1/workflows/{id}/evidence` with a 404, and the operator
> needs to be told to restart it, not shown a stack.

## `_adopt`, [line 42](../../../../backend/scripts/skill_from_rig.py#L42): Docstring

> Store one mined workflow as a skill, under a name a person typed.
>
> One workflow, never all of them. Adoption is the moment somebody says what
> a job is FOR, and a flag that did eight at once would be a person naming
> nothing eight times.

## `main`, [line 167](../../../../backend/scripts/skill_from_rig.py#L167): Comment

Code: `facility=args.facility,`

> No target_system. Each call files its credential reference under
> the host it actually went to, which is what a vault key is scoped
> by -- an earlier version of this script picked one host for a
> whole workflow and skipped the network recipe entirely wherever a
> job touched more than one, which cost 17 of 30 plans on this
> corpus. A cross-system job is the thing this project exists to
> capture; it is not the case to give up on.
