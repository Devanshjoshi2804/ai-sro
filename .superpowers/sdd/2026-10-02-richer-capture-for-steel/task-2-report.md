# Task 2 report
Status: done. Red recorded (ImportError for Choice / seen module), then green.
Tests: unit+contract 6184 passed; ruff, format, mypy --strict, lint-imports clean; check_code_notes clean for touched files (other files' stale anchors pre-exist).
Notes: path_shape renders ids as "*", tests use that. Test for identity builds the gesture with the file's `_on` helper.

## Fix round 1
Red: 34 of 46 new tests failed before the fix (route/cookie/mail/NaN/said_text/choice probes). Green after.
- said_text (outline.py) is now stricter and separate from `_said`, which is unchanged (pinned by a fixed-sample test): strips Unicode category C chars, drops emails, digit runs >= 6 (spaces/dashes allowed), password/passcode/secret/token with `:`/`=`/`is` and a value, base64-looking runs >= 20, sk_live_/ghp_-style prefixes.
- seen.py: routes drop on `=` in the hash and go through said_text (120 cap); cookie names need said_text(name)==name, domains a hostname regex + said_text, expires_at finite and <= 2100; mail_thread needs 16+ id chars and no redact_shapes change; _ms isfinite; choice index < K_CHOICE_OPTIONS (else choice dropped).
- Finding 8 not unified: outline._items/_texts are private with different cap order and use `_said`; reusing would change outline behaviour or need a new public alias for two one-liners.
- Gates: 6220 unit+contract passed, ruff, format, mypy --strict, lint-imports clean; check_code_notes 0 stale anchors (8 pre-existing dead notes elsewhere). Notes updated for outline/seen.

## Fix round 2
Red first: 38 new tests failed (huge ints, encoded routes, separators/fullwidth/obfuscated, wider phrases, JWT chunks, validation messages, dates, long words) and the 1 MB timing tests did not finish (quadratic email regex).
- I1: `_ms` and cookie expiry compare `0 <= raw <= limit` with no isfinite/float conversion (10**400, nan, inf all drop, no OverflowError).
- I2: said_text cuts input to 480 chars, NFKC-folds, strips category C, cuts to 120, then runs every (linear, bounded) regex; 1 MB adversarial inputs through said_text, place, cookies, mail ref run < 50 ms (9 shapes tested).
- I3: routes percent-decoded (3 passes, from 1000 chars) before the `=` test, path_shape and said_text; decoded form stored.
- M1/M2/M4/M6: separators ` ./-` in digit runs, fullwidth/`[at]`/`at host`/spaced `@`, IPs, PIN/CVV/OTP, wider phrases (pass, passwd, pwd, api key, authorization, Bearer) with a stop-word list so "Password is required" survives, `eyJ` guard, adjacent random-looking tokens, ISO dates allowed, plain long words allowed.
- M3, M5 and separator-less phrases documented in ADR 016. outline._said untouched (pinned test passes).
- Gates: 6068 unit passed, ruff, format, mypy --strict, lint-imports clean; check_code_notes clean for seen.py/outline.py.
