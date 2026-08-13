# Frontend walkthrough

Next.js App Router, TypeScript, Tailwind, shadcn/ui, TanStack Query.

## Structure

The frontend is **feature-sliced**, the opposite default to the backend. Its
slices are genuinely independent, and its dependency risk is import tangle
between features rather than business logic leaking into an adapter. See
[07-adr/006-layers-outside-features-inside.md](07-adr/006-layers-outside-features-inside.md).

```
frontend/src/
  app/                       Next.js App Router. Routing only.
    (dashboard)/
      recordings/page.tsx
      recordings/[id]/page.tsx
      skills/page.tsx
      skills/[id]/page.tsx
  features/
    recording/{api.ts,components/}
    skill/{api.ts,components/}
  components/ui/             shadcn. Added by CLI, not hand-edited.
  components/                shared app-level components
  lib/
    api/client.ts            typed fetch wrapper
    api/generated.ts         from backend OpenAPI. Never hand-edited.
    query.tsx                TanStack Query provider
    env.ts                   zod-validated env
```

`app/` here is Next's routing directory, **not** an architectural layer. This is
the documented collision when applying Feature-Sliced Design to Next.js: FSD's
own `app` layer conflicts with the framework's. We resolve it by not adopting
FSD's layer names at all — `app/` routes, `features/` own behaviour, `lib/` and
`components/` are shared. Same dependency direction, no name clash.

## Import rules

```
app/  ──▶  features/  ──▶  lib/, components/
```

- A feature **never** imports another feature. Shared code moves down to `lib/`
  or `components/`, or the two features were one feature.
- `app/` stays thin: routing, layout, and composing feature components. No
  business logic, no data shaping.
- Nothing imports upward.

## Server and client boundaries

Server Components are the default. A component gets `"use client"` only when it
needs state, an effect, or a browser API — anything else ships JavaScript for no
reason.

Push the boundary down: a server-rendered page containing one small client island
beats a client page containing server-fetched props.

## Data

- **Server state lives in TanStack Query.** No Redux, no Zustand, no context for
  anything the API owns.
- Client state (a form, a toggle) stays local until proven otherwise.
- Query keys are a typed factory per feature, not string literals scattered
  across components.

## The API contract

The backend OpenAPI document is the source of truth.

```bash
make types    # exports OpenAPI, regenerates frontend/src/lib/api/generated.ts
```

`generated.ts` is never hand-edited. A backend schema change that breaks the
frontend build is the mechanism working — that is the point of generating rather
than writing types.

## Adding a feature slice

Worked example: "show a recording's frames".

1. **Types** — regenerate with `make types`. Do not write the response type by
   hand.
2. **`features/recording/api/`** — one function per endpoint, using
   `lib/api/client.ts`. No `fetch` calls in components.
3. **`features/recording/hooks/`** — a `useRecordingFrames(id)` wrapping
   `useQuery`, with the key from the feature's key factory.
4. **`features/recording/components/`** — presentational. Takes data, renders it.
   Loading and error states are handled here, not in the page.
5. **`app/(dashboard)/recordings/[id]/page.tsx`** — a server component that
   composes the above. Thin.
6. `npm run lint && npm run typecheck`.

## Conventions

- `PascalCase` components, `camelCase` hooks and functions, `kebab-case` files.
- One component per file. If a file needs section comments, it is two components.
- Tailwind utilities inline; extract a component, not a `@apply` class, when it
  repeats.
- shadcn components come from the CLI. Wrap them to customise rather than editing
  `components/ui/` — the CLI overwrites on update.
- Accessibility is not optional. This product's own capture pipeline depends on
  accessible names existing; shipping a UI without them would be an odd position
  to hold.
- Never render a captured request or response body without the tenant scoping the
  API already applied. See [10-security-and-data.md](10-security-and-data.md).

## Screens in v0

| Route | Shows |
|---|---|
| `/recordings` | List, filterable by objective key. Pair two runs for induction. |
| `/recordings/[id]` | Frame timeline, network calls, a11y snapshot, screencast |
| `/skills` | Skills with their latest version and promotion stage |
| `/skills/[id]` | Steps, both plans, parameters with observed values, assertions, provenance, promote to shadow |
