# Two miners, one day

The precondition on phase 7's deletions, measured.

The spec's *Verification* section
([`2026-09-07-the-rig-into-the-backend-design.md:364`](../superpowers/specs/2026-09-07-the-rig-into-the-backend-design.md))
says this, and `Deletions, at the end` (line 294) repeats that nothing on its
list goes until it has been made and read:

> **The model path is measured against the rule-based one on one shared day,
> before either is deleted.** Both miners run over the same batches and the two
> answers are written down side by side: how many jobs each named, how many a
> person agrees with, and what one found that the other missed.
>
> This is a precondition on *Deletions*, not a nice-to-have, because the two do
> not meet anywhere. `MineObservations` reads `observations` and writes
> `task_candidates`; `mining_pass.mine` reads `gestures` and the pool and writes
> `workflows`. Neither reads the other's tables.

This is that measurement, taken from material already in the store. **No mining
pass was run to produce it and no workflow was started.** Everything below is a
read.

Measured **2026-09-11** against the development Postgres
(`postgresql://sro:sro@localhost:5432/sro`). It is a live store — the extension
was still uploading while these queries ran, so batch counts move. Anything that
matters is pinned to a day, not to a total.

### Running the SQL

`psql` was not installed on the machine this was written on either. Every query
below was run through SQLAlchemy against the same URL, the way
[`phase-5-walkthrough.md`](phase-5-walkthrough.md) describes. Save this and run
`cd backend && uv run python q.py 'select …'`:

```python
import asyncio, sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    e = create_async_engine("postgresql+asyncpg://sro:sro@localhost:5432/sro")
    async with e.connect() as c:
        for q in sys.argv[1:]:
            r = await c.execute(text(q))
            print(" | ".join(r.keys()))
            for row in r.fetchall():
                print(row)
asyncio.run(main())
```

---

## The two miners do meet, and the joint is the batch

The spec says the two paths "do not meet anywhere". That is true of the *tables*
they write. It is not true of the material they read, and this is what makes the
measurement possible at all.

One upload from the extension is written twice: once as an `observation_batches`
row, which is what `MineObservations` segments into `task_candidates`, and once
as a `gesture_batches` row whose `gestures` feed `mining_pool` and
`mining_pass.mine`. They carry **the same id**.

```sql
select (select count(*) from gesture_batches)      as gesture_batches,
       (select count(*) from observation_batches)  as observation_batches,
       (select count(*) from gesture_batches gb
          join observation_batches ob
            on ob.id = gb.batch_id and ob.tenant_id = gb.tenant_id) as matched;
```

```
 gesture_batches | observation_batches | matched
-----------------+---------------------+---------
             389 |                 520 | 389
```

Every gesture batch is an observation batch. So a `task_candidate` (which cites
`episodes[].batch_ids[].value`) and a `workflow` (whose steps cite gesture ids,
and every gesture carries `batch_id`) can both be resolved to the same list of
uploads, and from there to a calendar day. That is the shared ground. It was
already there; nobody had joined it.

## Which days are shared

Each miner's output, resolved back to the day the operator was actually working.

Rule-based:

```sql
select tc.tenant_id, date(ob.started_at) as d, count(distinct tc.id) as candidates
from task_candidates tc
cross join lateral jsonb_array_elements(tc.episodes) e
cross join lateral jsonb_array_elements(e->'batch_ids') b
join observation_batches ob
  on ob.id = b->>'value' and ob.tenant_id = tc.tenant_id
group by 1,2 order by 1,2;
```

Model:

```sql
select w.tenant_id, date(ob.started_at) as d, count(distinct w.id) as workflows
from workflows w
join workflow_steps s on s.workflow_id = w.id
cross join lateral jsonb_array_elements_text(s.cites) c(gid)
join gestures g on g.id = c.gid and g.tenant_id = w.tenant_id
join observation_batches ob on ob.id = g.batch_id and ob.tenant_id = g.tenant_id
group by 1,2 order by 1,2;
```

```
 tenant | day        | candidates | workflows
--------+------------+------------+-----------
 acme   | 2026-08-26 |         15 |         2
 acme   | 2026-08-27 |          3 |         1
 acme   | 2026-08-28 |          1 |         1
 acme   | 2026-08-31 |          9 |         2
 acme   | 2026-09-01 |         17 |         3
 acme   | 2026-09-10 |          7 |         0
 new    | 2026-09-02 |         11 |         0
 new    | 2026-09-10 |         20 |         2
```

**A shared day exists — six of them.** Five on `acme` and one on `new`. The
answer to question 1 is yes, and the precondition is therefore *measurable*,
which was not obvious before the join above was written.

Two rows are one-sided and they matter more than the shared ones. Keep them in
view: **`acme` 2026-09-10** and **`new` 2026-09-02** are days where the
rule-based miner produced answers and the model path produced nothing at all.

## One day in full: `new`, 2026-09-10

Chosen because it is the only shared day carrying the two-system demonstration
this architecture exists to test — the operator reads a value out of Gmail and
types it into the WMS.

### What the model named: 2 jobs

```sql
select w.id, w.title, w.systems, w.pass_id
from workflows w where w.tenant_id = 'new' order by w.created_at;
```

| id | title | systems |
|---|---|---|
| `wfl_365d0be081b9cea4e22252529b9e5cb6` | Create Customer Type DSS | `mail.google.com`, `bf56-kms-wms-web-np2.jdadelivers.com` |
| `wfl_7ceb3b15fd931b3fecf13140c08e633d` | Create Warehouse Equipment Type DDD | `mail.google.com`, `bf56-kms-wms-web-np2.jdadelivers.com` |

Seven steps each, both crossing the two systems in the right order, ten learnt
parameters between them (`mining_passes.learned_parameters` is 2 on
`pas_19ff744b…` and 8 on `pas_2cfd7e9c…`):

```sql
select w.title, s.ord, s.says, s.system, s.parameters
from workflows w join workflow_steps s on s.workflow_id = w.id
where w.tenant_id = 'new' order by w.title, s.ord;
```

```
Create Customer Type DSS  1  Opens the email requesting customer type DSS.          mail.google.com
                          2  Clicks the Add button…                                 jdadelivers.com
                          3  Types 'DSS' into the Customer Type field.              jdadelivers.com  ['DSS']
                          4  Checks the email again for the description.            mail.google.com
                          5  Types 'leaning SRO 3' into the Description field.      jdadelivers.com  ['leaning SRO 3']
                          6  Clicks save.                                           jdadelivers.com
                          7  Searches for the created customer type 'DSS'…          jdadelivers.com  ['DSS']
```

### What the rule-based path named: 20 candidates

```sql
select distinct tc.id, tc.host, tc.title, tc.named_by_model, tc.times_seen, tc.status
from task_candidates tc
cross join lateral jsonb_array_elements(tc.episodes) e
cross join lateral jsonb_array_elements(e->'batch_ids') b
join observation_batches ob on ob.id = b->>'value' and ob.tenant_id = tc.tenant_id
where tc.tenant_id = 'new' and date(ob.started_at) = date '2026-09-10'
order by tc.host, tc.title;
```

```
 host               title                                       by_model  seen  status
 jdadelivers.com    Create a customer type                      True      4     taught
 jdadelivers.com    Create equipmentTypes on …jdadelivers.com    False     2     new
 jdadelivers.com    Read codes on …jdadelivers.com               False     1     new
 jdadelivers.com    Read codes on …jdadelivers.com               False     1     new
 jdadelivers.com    Read equipmentTypes on …jdadelivers.com      False     1     new
 jdadelivers.com    Read warehouses on …jdadelivers.com          False     1     new
 jdadelivers.com    Read WMEquipment on …jdadelivers.com         False     1     new
 mail.google.com    Create bv on mail.google.com                 False     1     new
 mail.google.com    Create bv on mail.google.com                 False     4     new
 mail.google.com    Create fd on mail.google.com                 False     1     new
 mail.google.com    Create fd on mail.google.com                 False     1     new
 mail.google.com    Create fd on mail.google.com                 False     2     new
 mail.google.com    Create fd on mail.google.com                 False     1     new
 mail.google.com    Create s on mail.google.com                  False     2     new
 mail.google.com    Create s on mail.google.com                  False     8     taught
 mail.google.com    Create s on mail.google.com                  False     1     new
 mail.google.com    Create u on mail.google.com                  False     1     new
 mail.google.com    Create u on mail.google.com                  False     1     new
 mail.google.com    Create u on mail.google.com                  False     1     new
 mail.google.com    Create u on mail.google.com                  False     9     new
```

Twenty rows. Thirteen of them are Gmail's own XHR path fragments with `Create`
in front — `bv`, `fd`, `s`, `u` are not tasks, they are URL segments.

### Side by side

Both miners saw the same uploads, and neither saw the whole day:

```sql
with d as (select id from observation_batches
           where tenant_id='new' and date(started_at)=date '2026-09-10'),
     cb as (select distinct b->>'value' bid from task_candidates tc
            cross join lateral jsonb_array_elements(tc.episodes) e
            cross join lateral jsonb_array_elements(e->'batch_ids') b
            where tc.tenant_id='new'),
     wb as (select distinct g.batch_id bid from workflows w
            join workflow_steps s on s.workflow_id=w.id
            cross join lateral jsonb_array_elements_text(s.cites) c(gid)
            join gestures g on g.id=c.gid and g.tenant_id=w.tenant_id
            where w.tenant_id='new')
select count(*) as batches_that_day,
       count(*) filter (where cb.bid is not null) as cited_by_rule,
       count(*) filter (where wb.bid is not null) as cited_by_model,
       count(*) filter (where cb.bid is not null and wb.bid is not null) as both
from d left join cb on cb.bid=d.id left join wb on wb.bid=d.id;
```

```
 batches_that_day | cited_by_rule | cited_by_model | both
------------------+---------------+----------------+------
               87 |            22 |              7 |    7
```

Every batch the model cited was also cited by the rule-based path. Sixty-five of
the day's eighty-seven uploads are cited by neither. That is not a fair
criticism of either miner on its own — a batch can be a page load with nothing
in it — but it does mean "the model covered the day" is not a claim this
measurement supports.

**The jobs, matched by hand:**

| The job a person did | Rule-based said | Model said |
|---|---|---|
| Read a mail, create customer type DSS in the WMS | `Create a customer type` **and** `Create s on mail.google.com` — two candidates, never joined | `Create Customer Type DSS` — one job, both systems, every typed field a parameter |
| Read a mail, create warehouse equipment type DDD | `Create equipmentTypes on …jdadelivers.com` **and** `Create bv on mail.google.com` — two candidates, never joined | `Create Warehouse Equipment Type DDD` — one job, both systems, every typed field a parameter |
| — | 16 further rows: 5 `Read …` on the WMS, 11 more Gmail fragments | — |

**On this day the model path names two jobs and the rule-based path names two
jobs eighteen times over, in halves, one system each.** The rule-based miner has
a cross-system join — `JoinKind.WORKFLOW` in
`backend/src/sro/domain/observation/candidate.py:89`, proposed by
`ProposeAboutCandidates` — and it has never once fired:

```sql
select joins->0->>'kind' as kind, count(*) from task_candidates
where joins::text <> '[]' group by 1;
```

```
 kind    | count
---------+-------
 variant |     2
```

Two rows out of eighty carry any join at all, both `variant`, both
`answered: null` — proposed, never answered by a person.

## How many a person agrees with

The spec asks for this and it is the number that does *not* favour the model.

A person's agreement is recorded in two different places, one per path. On the
rule-based side, pressing Teach moves a candidate to `taught` and writes a
`skill_id`:

```sql
select tenant_id, status, count(*) from task_candidates group by 1,2 order by 1,2;
select id, title, host, skill_id from task_candidates where status='taught';
```

```
 acme  new     44      acme  taught   5
 new   new     27      new   taught   4
```

Nine candidates of eighty were taught into real skills. Four of them are on
`new`: `Create a customer type`, `Create a supplier`, `Create a work area` — and
`Create s on mail.google.com`, which is a skill built on a URL fragment.

On the model side, agreement is an `offer` the operator accepts:

```sql
select o.id, o.tenant_id, w.title, o.fate, o.at
from offers o join workflows w on w.id = o.workflow_id order by o.at;
```

```
 off_9d36b26c…  acme  Create a Warehouse Equipment Type  diverged  2026-09-10 14:59
 off_93b544eb…  new   Create Customer Type DSS           diverged  2026-09-10 16:17
 off_eb3c545e…  new   Create Customer Type DSS           expired   2026-09-10 16:20
 off_83c21d7d…  new   Create Customer Type DSS           diverged  2026-09-10 16:20
 off_5c0a0b3f…  new   Create Customer Type DSS           expired   2026-09-10 16:26
```

Five offers, three `diverged`, two `expired`, **zero accepted.**

So on the spec's own third criterion the score is **9 – 0 to the rule-based
path**. A model workflow has never been agreed with by a person, because
`workflow_runs` is still empty and step 8 of the phase-5 walkthrough has never
been pressed. That is a gap in the *evidence*, not proof the workflows are
wrong — but it is the number, and it is the one that must be reported.

## What each found that the other missed

### The model found

**The join.** Both two-system jobs, as single jobs, with the mail step in
sequence and the typed value carried across. The rule-based path produced the
same work as four unrelated candidates on two hosts and proposed no join between
them. This is the finding the whole architecture was for, and it is real.

**Parameters.** `learned_parameters` totals 14 on `acme` and 10 on `new` across
eleven passes; `task_candidates` has no parameter concept at all. Nothing in the
rule-based output could be replayed with a different value.

### The rule-based path found

**Two whole days the model path never read.**

```sql
select g.tenant_id, date(ob.started_at) d,
       count(*) gestures, count(p.gesture_id) in_pool
from gestures g
join observation_batches ob on ob.id=g.batch_id and ob.tenant_id=g.tenant_id
left join mining_pool p on p.gesture_id=g.id and p.tenant_id=g.tenant_id
group by 1,2 order by 1,2;
```

```
 acme  2026-09-10   48 gestures    0 in pool
 new   2026-09-02    0 gestures    —
 new   2026-09-10  151 gestures   89 in pool
```

- **`acme` 2026-09-10**: 48 gestures captured, **none of them ever entered the
  mining pool** — the last `acme` pass ran at 09:41 and the gestures arrived
  after it. The rule-based path produced 7 candidates from that day, including
  `Create customerTypes on …jdadelivers.com` (`cnd_60fffb29…`), a write.
- **`new` 2026-09-02**: 127 observation batches, 750 events, **zero gestures**.
  The model path has no evidence for that day whatsoever. The rule-based path
  produced 11 candidates from it, two of which a person taught into skills:
  `Create a supplier` (`cnd_2d10af22…` → `skl_00714071…`) and `Create a work
  area` (`cnd_b9aa2d27…` → `skl_960347425…`).

`Create a supplier` is a real warehouse job, taught by a real person, and **no
workflow anywhere in the store names it.** Deleting `MineObservations` today
deletes the only path that ever found it.

Whether that is a capability gap or a scheduling one is not settled by this
measurement. The 2026-09-10 `acme` case looks like scheduling — run another pass
and it would probably be found. The 2026-09-02 `new` case is not: no gestures
were captured at all, which is a gap in the *upload* path, not in the miner.
Either way, the rule-based path had the answer and the model path did not.

**One write the model demoted to a footnote.** `cnd_07332b0efa6a492e9b74081f328cfcae`,
`Update addresses on bf56-kms-wms-web-np2.jdadelivers.com`, 2026-08-31: 32 calls,
19 gestures, one batch. That batch is cited by the model's `Create a Carrier
Cross Reference`, where the same activity appears as step 7, *"Optionally lookup
and select a COD Address"*.

```sql
with cb as (select distinct b->>'value' bid from task_candidates tc
            cross join lateral jsonb_array_elements(tc.episodes) e
            cross join lateral jsonb_array_elements(e->'batch_ids') b
            where tc.id='cnd_07332b0efa6a492e9b74081f328cfcae'),
     wb as (select distinct w.title, g.batch_id bid from workflows w
            join workflow_steps s on s.workflow_id=w.id
            cross join lateral jsonb_array_elements_text(s.cites) c(gid)
            join gestures g on g.id=c.gid)
select cb.bid, wb.title from cb left join wb on wb.bid = cb.bid;
```

```
 bat_5b4b5fa9…_f668a1e6_3538 | Create a Carrier Cross Reference
```

The model is probably right and the rule-based path probably over-split. But a
`PUT` to an address endpoint is a write against a customer's WMS, and the two
miners disagree about whether it is a job. A person has to say which. Nobody has.

## Quality, unflattered

Neither output is good. Counting them as "49 versus 9" flatters the rule-based
path; counting the model's 9 as nine warehouse jobs flatters the model.

**The rule-based path names almost nothing itself.** Of 80 candidates, 71 carry
a machine-assembled `<Verb> <url-fragment> on <host>` title from `_VERBS` in
`backend/src/sro/application/observation/mine.py:31`. The nine that read like a
task were all named by a model:

```sql
select tenant_id, named_by_model, count(*) from task_candidates group by 1,2;
```

```
 acme  False  43     acme  True  6
 new   False  28     new   True  3
```

The comparison is not "rules versus a model". It is "a model asked to write a
sentence on the front of a clustered signature" versus "a model asked to read
the gestures". Only the second one produced a cross-system job.

**The rule-based path duplicates.** `Create an activity code` exists twice
(`cnd_3dab78d0…`, `cnd_de27da62…`), each `times_seen` 4, each holding the other
as a `variant` join nobody answered — and `Create activityCodes on
…jdadelivers.com` (`cnd_035c95d9…`) is a third row for the same work. Same
pattern on `Create a work area` (`cnd_9c3a5d68…` taught, `cnd_521abfe2…` not)
and on the `localhost` rows, which come in `starts_on` present / `starts_on`
empty pairs.

**Twenty of `acme`'s 49 candidates are the console recording itself.**

```sql
select tenant_id, host, count(*) from task_candidates group by 1,2 order by 1,3 desc;
```

```
 acme  bf56-kms-wms-web-np2.jdadelivers.com  24
 acme  localhost                             20
 acme  mail.google.com                        5
 new   bf56-kms-wms-web-np2.jdadelivers.com  17
 new   mail.google.com                       13
 new   blueyonderalphaus.b2clogin.com         1
```

`Read skills on localhost`, `Read candidates on localhost`, `Create teach on
localhost` — the operator using AI-SRO, mined as warehouse work. One of them,
`Teach a candidate` (`cnd_78d5d352…`), was taught into a skill.

**And the model path's nine are not nine either.** Already recorded at the foot
of [`phase-5-walkthrough.md`](phase-5-walkthrough.md) and re-checked here:

```sql
select id, title, systems, same_as from workflows order by tenant_id, created_at;
```

- `Review Video Recordings for Teach Task` (`wfl_a5104a4e…`, `http://localhost:3000`)
  is the console recording itself. The same artefact the rule-based path makes
  twenty of, the model makes one of — an improvement of degree, not of kind.
- `Search for Work Areas` (`wfl_6b062d20…`) is the SSO hop. Its `systems` are
  `b2clogin`, `keycloak` and the WMS; its first step is *"Log in to the
  system."*; and **every one of its six steps has `system = NULL`**, so nothing
  could execute it.
- `Create Customer Type DSS` and `Create Warehouse Equipment Type DDD` bake a
  parameter value into the title. A second demonstration with a different value
  joins a job named after the first.
- `Create a Work Area` (`wfl_d4a551f1…`) carries
  `same_as = wfl_bad4233779457a6fd2a5d0574b9f6628`, which is `Create a Warehouse
  Equipment Type`. Those are two different jobs. The dedup is wrong.
- `Create a Work Activity` (`wfl_d07bcf1c…`) is 25 steps: *"Click Add"*, save,
  *"Click Add again"*, save, *"Click the Add button"*, save, *"Click Add to
  create a fourth operation"*, save. Four separate creations glued into one
  workflow, with eleven parameter values that belong to four different runs.

**So: 9 workflows, of which 2 are artefacts, 1 is unexecutable, 2 are misnamed,
1 is wrongly deduped and 1 is four jobs in a trench coat.** The honest count of
model-mined warehouse jobs a person would recognise and want offered is **three**
— `Create a Carrier Cross Reference`, `Create a Work Area`, and one of the two
cross-system jobs. Against the rule-based path's nine taught candidates, of which
one is a Gmail fragment and one is the console, leaving **seven**.

**The model path costs money and the rule-based path's cost is unmeasured.**

```sql
select tenant_id, count(*) passes, sum(proposed), sum(kept), sum(rejected),
       round(sum(cost_usd)::numeric,4) usd, count(*) filter (where error is not null) errored
from mining_passes group by 1 order by 1;
```

```
 acme  9 passes  21 proposed   7 kept  1 rejected  $5.4028  1 errored
 new   2 passes   7 proposed   2 kept  0 rejected  $0.2950  0 errored
```

$5.70 for nine workflows. Twenty-eight proposals became nine rows; the
nineteen that vanished are not all in `rejected` (which totals 1), so the
`proposed`/`kept`/`rejected` accounting does not close and something is dropping
proposals silently. One `acme` pass spent **$2.00 and returned nothing** —
`pas_4a6b0cc0…`, `error: truncated: the answer hit the 65536 output-token
ceiling after 2610 tokens`. There is no comparable figure for the rule-based
path: the `NameCandidate` calls behind `named_by_model` are not written to
`mining_passes` and `model_calls` holds only 7 rows, all from the execution
planner. **"The model path is cheaper" is not a claim this store can support in
either direction.**

---

## What this does not prove

- **It is not a controlled run.** The spec asks for both miners run over the
  same batches. That did not happen. What happened is that both miners had
  already run, at different times, over an overlapping set of uploads, and this
  document joins their outputs after the fact. The 87-batch day where the model
  cites 7 and the rules cite 22 is not two miners given the same input; it is two
  miners given whatever each was given.
- **It cannot say a dropped candidate was correctly dropped.** `Read nonpaged on
  …jdadelivers.com` is obviously noise. Whether `Update addresses` is noise is a
  judgement, and no person in this store has made it — the `variant` joins sit
  `answered: null` and the candidates sit `new`.
- **It says nothing about execution.** `workflow_runs` and `workflow_run_steps`
  are still empty. Not one mined job of either kind has ever been run end to end
  against the WMS. Every offer diverged or expired.
- **It is one tenant-pair on a development database**, with `localhost:3000`
  traffic mixed into the corpus on `acme`. A customer's day looks nothing like
  this.
- **The `new` 2026-09-02 gap is unexplained.** 127 observation batches and zero
  gestures on the same day, same tenant, same extension. Until somebody knows
  why, "the model path missed two taught skills" and "the upload path was broken
  that day" are indistinguishable from this table.

## Verdict on the precondition

**Not met. Phase 7's deletions must not proceed on this document.**

Of the three things the spec asks for, this measurement supplies two and a half:

| The spec asks | Status |
|---|---|
| Both miners run over the same batches | **No.** Outputs joined after the fact over an overlap neither was given deliberately. |
| How many jobs each named | **Yes.** 20 candidates vs 2 workflows on `new` 2026-09-10; 80 vs 9 overall; 7 vs 3 after artefacts. |
| How many a person agrees with | **Yes, and badly.** 9 candidates taught vs 0 workflows accepted, from 5 offers. |
| What one found that the other missed | **Yes.** Model: the cross-system join, and parameters. Rules: two whole days, including the taught skill `Create a supplier`, which no workflow names. |

Three things are missing, and they are small:

1. **One pass over one shared day, deliberately.** Pick `new` 2026-09-10 — the
   gestures are still in `mining_pool` (89 rows, none retired) and the
   observation batches are still there. Run `MineObservations` over
   `since = 2026-09-10T00:00Z` and one `mining_pass` over the same window, and
   record both. That is one pass, roughly $0.15 by the figures above, and it
   converts this document from an after-the-fact join into the controlled
   comparison the spec asked for.
2. **A person answering the two open questions.** Is `Update addresses` a job?
   Is `Create a supplier` — taught, in a skill, unnamed by any workflow —
   reachable by the model path at all, or only by the rules? Until the second is
   answered, the first bullet of `Deletions` removes a capability nobody has
   shown the replacement has.
3. **One accepted offer.** Zero of nine model workflows has been agreed with by
   a person. Deleting the path that has nine agreements in favour of the path
   that has none is a decision that needs at least one data point. It is step 8
   of [`phase-5-walkthrough.md`](phase-5-walkthrough.md), still unpressed.

The safe subset, if phase 7 wants to move: `new_agent_arch/` and the
`from_rig` / `adopt_rig_workflow` / `network_from_rig` / `mirror_backfill`
bullet are about the *rig*, not about the rule-based miner, and nothing in this
measurement defends them. The first bullet — `segment.py`, `mine.py`,
`propose.py`, the miner sweep, the `candidates` router — is the one this
precondition guards, and it stays.

---

## Half of that pass, run deliberately — 2026-09-11

The first missing thing above is a pass over one shared day given to both
miners on purpose. **The rule-based half has now been run that way.** The model
half has not: it costs real money and the decision to spend it is the operator's,
so it is still owed. What follows is therefore one side of a controlled
comparison, not both — read it as such.

```bash
curl -s -X POST "localhost:8000/v1/candidates/mine?hours=20" -H "Authorization: Bearer $TOKEN"
```

```json
{"episodes":50,"candidates_seen":45,"candidates_new":14,"occurrences_new":30}
```

Twenty hours back from 07:10 UTC on 2026-09-11 covers `new` 2026-09-10's window
in full — the pool's own rows run 15:28 to 16:22 UTC that day — and takes in
2026-09-11's 23 batches as well, which are this session's own traffic and are
named in the table below so nobody counts them as warehouse work.

Tenant `new` afterwards, by `times_seen`:

```sql
select title, host, times_seen, named_by_model, status
from task_candidates where tenant_id = 'new'
order by times_seen desc, title;
```

```
Create s on mail.google.com                                    12  model=f  taught
Create u on mail.google.com                                    11  model=f  new
Create a customer type          …jdadelivers.com                8  model=t  taught
Create a supplier               …jdadelivers.com                5  model=t  taught
Create a work area              …jdadelivers.com                4  model=t  taught
Create bv on mail.google.com                                    4  model=f  new
Create equipmentTypes on …jdadelivers.com                       4  model=f  new
…and 18 more, of which 16 are `Create <two letters> on mail.google.com`
```

Thirty-one candidates, and the shape of the answer is the finding.

## The rule-based path cannot represent a two-system job. Structurally.

Not "did not on this day" — cannot, and the code says so in its own words.

```python
# domain/observation/candidate.py:150
    host: str
```

A candidate carries **one** host. `JoinKind.WORKFLOW`
(`candidate.py:89`) is the only bridge, and its own docstring reads:

> Two halves of one piece of work, in two systems. Segmentation runs each host
> on its own stream, so an episode is always one host's: **this is a shape no
> single candidate can ever have.**

A `WORKFLOW` join does not assert the pair; it *asks*, and `JoinAnswer` is
supplied by a person. The store holds two join rows in total, both `variant`,
both unanswered — so the question has never once been put.

This is visible in the table above without any of that reading. On the day the
operator did two cross-system jobs, the rule path returned the halves:
`Create a customer type` on the WMS and `Create s on mail.google.com` beside it,
`Create equipmentTypes on …jdadelivers.com` and `Create bv on mail.google.com`
beside that. Four host-local candidates for two jobs, and nothing anywhere
saying they are pairs. The model path returned two jobs, each naming both
systems in order, with the mail read between fields as a step.

So the part of the precondition that asks *what one found that the other
missed* has a harder answer than it did: the cross-system join is not something
the rule-based path missed on this corpus. It is something that path has no
place to put.

**This does not settle the precondition.** The rules still found two whole days
the model never read and a taught skill no workflow names, and the model path
still has 0 accepted offers against 9 taught candidates. Both of those survive
this section untouched, and the model half of the paired pass is still owed.
