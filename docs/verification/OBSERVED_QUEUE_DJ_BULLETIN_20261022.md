# Observed-queue DJ bulletin — local source qualification

The existing Forecast guidance describes a contiguous observed prefix of up to
five actual queued Spotify tracks, targeting about fifteen minutes after at
least three when durations allow. Shorter or incomplete prefixes remain shorter.
Optional genres come from exact artist IDs. Four authored Persona variants use
all five supported languages; no recording-level audio measurements are inferred.

The read-only external queue is private owner context. Shared display Forecasts
retain their prior current-context narrative. No upcoming art, actions, playback,
new Moment, Presence-budget expenditure, model call or persistent queue storage
is introduced. Original owner/account/source/Session, actor revision, command,
actual output ID/occurrence and recording/state occurrence are fenced before
awaits and again inside commit locks. A→B→A and same-name output changes cannot
reuse an earlier occurrence. Both wire `valid_until` and server admission retain
the original thirty-second mono/wall deadline; reads do not renew it.

Local validation on the final product bytes:

- Full suite: 3168 tests in 84.979 seconds, PASS with seven existing skips.
- Ruff: nine changed Python files PASS; full diff whitespace PASS.
- Eight isolated actual HA2026.10.0 HTTP harnesses PASS; all241 product hashes
  equal before/after and the sole owned no-network/no-host-mount container removed.
- Queue harness: 20 locale/Persona paired-HTTP cases, pure reads, same-name output
  change, recording A→B→A, delayed command/revision withdrawal, and owner/shared
  separation. Only external Spotify/CDN answers are synthetic fixtures.
- Seven existing current wire derivatives and the avatar semantic derivative
  regenerated from original retained receipts; historical raw evidence preserved.
- Review found wire-expiry, command/recording/output-ABA and lock-wait gaps; fixes
  and original failed runs are retained in the private evidence dossier.

The tracked actual-HA derivative is
`examples/client_contracts/session_forecast_v1/observed-queue-bulletin-actual-ha.json`.
Original local evidence lives in the existing `core-window-20261021-12h` dossier,
under `dj-bulletin-ha-lab/run9` and `dj-bulletin-final9-fullsuite.log`.

This is local source qualification. Exact committed independent review, normal
CI, protected merge, canonical post-merge qualification, HA-dev/prod installation,
visible native acceptance and live Spotify behavior remain distinct gates. No
merge or install is claimed. Peter's one-PR-until-explicit-merge policy applies.
The earlier merged consolidation's separate GitHub Final qualification blocker
is preserved and is not silently replaced by these receipts.
