# Code standards

Everything mechanical is enforced by tooling. This document covers the
judgement calls tooling cannot make.

Run `make lint` before every push. It is the same command CI runs.

## Comments and docstrings

The rule: **code says what; the why lives in `docs/`.** Backend source carries
no comments and no docstrings. The explanation of a line, function or module
goes in [`docs/code-notes/`](code-notes/README.md), in the file that mirrors the
source path (`backend/src/sro/x/y.py` → `docs/code-notes/backend/src/sro/x/y.py.md`),
under a heading naming the function or class and the line.

Rationale that spans more than one module belongs in the numbered `docs/` pages —
written once, linked from the notes. A design decision restated in six modules
rots in six places the first time the design changes.

Exceptions, kept in code because they are read at runtime or by tools:

| Kept in code | Why |
|---|---|
| Docstrings under `backend/src/sro/interface/http/` | FastAPI turns them into `frontend/openapi.json` |
| Docstrings of pydantic models and of classes that appear in the OpenAPI schema | They become schema descriptions |
| `# noqa`, `# type: ignore[...]`, `# pragma`, `# fmt:` | Tool directives |

A deliberate shortcut is still named: put the `ponytail:` note (its ceiling and
upgrade path) in the code-notes file; the index lists every one.

If a field needs a note to be understood, first try renaming it.

Outside the exceptions above, prose in `src/` should measure close to 0%. Any
comment or docstring in a diff is a review comment: move it to the notes file.

Measure it:

```bash
cd backend && uv run python -c "
import ast,pathlib
t=d=0
for p in pathlib.Path('src/sro').rglob('*.py'):
    s=p.read_text(); t+=len(s.splitlines())
    for n in ast.walk(ast.parse(s)):
        if isinstance(n,(ast.Module,ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)):
            x=ast.get_docstring(n)
            if x: d+=len(x.splitlines())+2
    d+=sum(1 for l in s.splitlines() if l.strip().startswith('#'))
print(f'{d/t*100:.0f}%')"
```

## Typing

- `mypy --strict` over all of `src`. No `# type: ignore` without a comment
  naming the upstream cause.
- `domain` and `application` additionally forbid explicit `Any`. The single
  exception is `application/induction/jsonutil.py`, declared in `pyproject.toml`:
  JSON genuinely is dynamic, and confining `Any` there keeps the escape hatch
  from leaking.
- Every timestamp is timezone-aware. Entities reject naive datetimes; ruff `DTZ`
  catches the calls that would produce them.

## Errors

- Raise `DomainError` subclasses from `domain` and `application`.
- `interface/http/errors.py` maps them to responses in **one** handler. A new
  error type needs no web-layer change unless it wants a distinct status code.
- Infrastructure failures are not `DomainError`. `BrowserUnavailable` means the
  provider is down, not that the request was wrong — it maps to 503.
- Never catch broadly to keep going. `contextlib.suppress` with a named
  exception and a comment is acceptable; bare `except Exception` is not.

## Ports

Add a port when the application needs an **effect**: storage, network, time,
randomness, a browser. These make code untestable and are what later phases will
swap.

Do **not** add one for:

- A pure calculation. A function is not a dependency — `diff.parameterise` has no
  port because it computes rather than acts.
- A single implementation with no second use in sight. That is an interface tax
  with no payer.

Every port gets a fake in `tests/unit/fakes.py`. If it cannot be faked in a few
lines, it is describing an implementation rather than a capability.

## Use cases

- One file, one class, one public `execute` (or a small pair of named entry
  points, as `FinishRecording` has `seal`/`abandon`).
- Dependencies injected in `__init__`. Nothing is constructed inside a use case.
- `RequestContext` is always the first argument.
- Orchestration only. A business rule enforced in a use case is enforced only on
  the paths that remember to call it — it belongs on the entity.

## Naming

- Domain vocabulary comes from [06-glossary.md](06-glossary.md). One name per
  concept, everywhere: never `demo` in one module and `recording` in the next.
- No invented abbreviations. `parameterisation`, not `param_res`.
- Private helpers are `_prefixed` and sit below the public API in the file.

## Tests

- `tests/unit` — no Docker, no network, no real clock. Everything through fakes.
- `tests/integration` — testcontainers Postgres and MinIO. Only place
  transactional behaviour is proved.
- Test names are sentences: `test_a_derived_parameter_cannot_be_used_before_it_is_produced`.
- Build fixtures with `tests/factories.py` so each test names only the fields it
  is about.
- Comments in tests explain what would go wrong in production if the assertion
  failed. That is the one place a longer comment earns its space.

## Frontend

See [04-frontend-walkthrough.md](04-frontend-walkthrough.md).
