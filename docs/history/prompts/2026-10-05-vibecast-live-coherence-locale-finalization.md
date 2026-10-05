# VibeCast live playback coherence and locale Finalization

- Directive: `DJC-FIRST-SLICE-AFTER-PLANNING-V1-20261003`
- Assignment: `DJC-VIBECAST-PI-OWNER-HANDOFF-V1-20261004`
- Source PR: [#1116](https://github.com/pcvantol/djconnect/pull/1116)
- Reviewed head: `108e720b9ac488bc76107c6d95afdfe133cc6b42`
- Protected merge: `a187f7c6f7f91f4d5c25ff685323e528ba97449c`
- Shared tree: `4dfc3a3aeab278bb319c72bd3157905aebe1ea28`
- Product result: recurring Spotify polling no longer waits on Track Insight; superseded enrichment and transactional Session state fail closed; renderer Moments are correlated to the current playback item; explicit or Assist-derived Session locale is normalized to `en`, `nl`, `de`, `fr` or `es`.
- Independent review: pause/reload retry, Assist fallback, locale clamping, Discover accounting, stale coordinator mutation and cancellation-race findings corrected; final result reported no actionable correctness issue.
- Local validation: 1,920 passed, 14 skipped, 793 subtests; targeted Ruff and diff check passed.
- Exact-main validation: [Validate](https://github.com/pcvantol/djconnect/actions/runs/37347227997) passed 1,535 tests with 49 skips; [CodeQL](https://github.com/pcvantol/djconnect/actions/runs/37347227306) passed.
- Publication: [artifact run](https://github.com/pcvantol/djconnect/actions/runs/37347516248) and [evidence run](https://github.com/pcvantol/djconnect/actions/runs/37347516789) passed. The internal archive SHA-256 is `d542a576c50e1a5ea95ab39d2cc1678265b749a356866583304a821076f197cf`; redacted evidence reports all required checks PASS and coverage digest `7ce8fdde8da01c86d20591e00e3f761834dff5b66b4c9df154ed4e810ccf6a17`.
- Product boundary: `PI_QUAL=OPEN`. Exact HA-dev installation, Apple locale handoff and the physical same-Session non-terminal Dutch update, reconnect, Runtime-end/Idle and token/privacy receipts remain required. No deployment, second slice or Cast follow-on occurred.
