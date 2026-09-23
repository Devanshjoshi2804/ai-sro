# Notes for `backend/src/sro/infrastructure/knowledge/seed_skills.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/knowledge/seed_skills.py`](../../../../../../../backend/src/sro/infrastructure/knowledge/seed_skills.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/knowledge/seed_skills.py#L1): Docstring

> Turn recorded Blue Yonder flows into skills, without teaching them again.
>
> Run with `make seed-skills`. Re-runnable by construction: a flow whose objective
> already has a skill is skipped, so a repeat run over a growing corpus only ever
> seeds what is new.
