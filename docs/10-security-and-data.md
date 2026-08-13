# Security and data handling

**This document does not restrict what is captured.**
[11-capture-completeness.md](11-capture-completeness.md) is the authority on
that, and the answer there is *everything*: full headers, full bodies, cookies,
storage, console, CDP initiator chains, the accessibility graph, per-action
screenshots, screencast video, narration audio, and the raw CDP stream verbatim.

This document is how that is held safely, so total capture stays defensible.

## The three planes

| Plane | Contents | Rule |
|---|---|---|
| **Evidence** — capture store | Everything, verbatim | Encrypted at rest, tenant-scoped, access-audited |
| **Skill** — workflow repository | Full header set and shape; secret **values** by vault reference | Skills are versioned, shared across facilities and exportable |
| **Telemetry** — logs, traces, metrics | Names, shapes, sizes, hashes. Never a body or a secret value. | Telemetry fans out to third-party backends with different retention |

Credentials are captured, stored **and used**. A `NetworkPlan` records that a
request carried `Authorization: Bearer <…>` and points at the vault entry; the
executor resolves it at run time and sends the real value.

Nothing is lost. A secret simply is not copied into an artifact designed to
travel between sites — which is a storage decision, not a capture decision.

## Tenancy

`tenant_id` is on every row and is the first parameter of every repository
method, never defaulted. Filtering happens in the `WHERE` clause, never in Python
afterwards.

`NotFound` is raised identically for "missing" and "another tenant's". The
distinction would confirm an id exists elsewhere.

Object storage keys are tenant-first (`<tenant>/<recording>/<kind>/<name>`) so a
bucket policy or lifecycle rule scopes per tenant without parsing the path.

Every integration test touching a repository seeds **two** tenants and asserts
only one comes back.

## Credentials

- Captured in full, stored encrypted, resolvable by the executor.
- No secret in source, in a fixture, or in a committed file.
- Configuration comes from environment via `pydantic-settings`; the frontend
  validates its env with zod at boot.
- Session state (cookies, tokens, MOCA session keys) is encrypted at rest with an
  enforced max age.
- Open question for the pilot: customer-held credentials with delegated sessions
  versus system-held. The former is a far smaller review surface.

## Consent and authorisation

Settled in the pilot agreement, not afterwards:

1. **Deliberate demonstration, not passive capture.** "Teach the system this
   task" is clean on consent, on personal data, and on optics where union
   agreements apply. It is also what makes total capture acceptable — the
   operator knows the session is being recorded in full.
2. **Written customer authorisation** for automating a vendor's UI and
   intercepting its traffic.

## Retention

Recordings are evidence — a skill's provenance cites them — so deletion is
policy, never incidental.

- Per-tenant retention window on media artifacts (`RAW_EVENTS`, `VIDEO`,
  `AUDIO`, `SCREENSHOT`), applied by an object-store lifecycle rule.
- Frames, skills and the API catalogue outlive the media, so a skill stays
  explainable after the screencast expires.
- Deletion is recorded, not silent.

## Browser isolation

One session per demonstration, closed when the recording finishes. The
`RecordingWorkflow` reaper collects abandoned sessions — a browser left open is
an authenticated WMS session sitting idle.

Steel runs inside the deployment boundary, which is why a self-hostable browser
was chosen over a SaaS one.

## Audit trail

Every state change carries actor and timestamp: who demonstrated, who induced,
who promoted. When writes exist they add intent, before, after and verification
result, and the trail is immutable.

`promoted_by` and `induced_by` are not optional. Governance that cannot answer
"who approved this" is decoration.

## Reporting a vulnerability

Do not open a public issue. Contact the maintainers directly.
