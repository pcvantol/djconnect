# Storage Schema Runner Compatibility

Date: 2026-08-03

## Objective

Restore Execution Host compatibility after an Inbox prompt failed before
execution because the repository declared storage schema 6 while the active
runner advertised support only through schema 5.

## Delivered outcome

PR [#727](https://github.com/pcvantol/djconnect/pull/727), **Support current
engineering storage schema**, merged as
`75b7cf2f7595016e6ff1f6e1ab6ca7ec7ea1a5af`.

The runner compatibility matrix now includes schema 6, retaining support for
schemas 1 through 5. A regression test requires the default runner
compatibility to accept the current repository manifest. The change restores
valid prompt admission without changing Forge, the Execution Host Contract,
product behavior or engineering logic.

## Validation evidence

- `python3 -m unittest tests.engineering.test_execution_host`: 88 passed.
- `python3 -m unittest discover -s tests/engineering`: 243 passed.
- `./tools/engineering/dj-engineer qualify`: 39/39 passed.
- Current repository manifest accepted by the active runner compatibility.
- `git diff --check`: passed.

## Follow-up

The recommended next bounded Execution Host increment is Preflight Level 3
(Capability Preflight), which should surface runner-contract incompatibility
before Inbox acceptance.
