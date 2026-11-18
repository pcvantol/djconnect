# Session For-you locale, Mood refresh and continuation qualification

Owner scope: English/Dutch Core/Apple correction coordinated with `apple 3`.
Product Development correction in the existing Session/Settings3/For-you owners;
no new recommender, playback engine, client intelligence or authorization source.

The preparation now uses the accepted Session locale rather than falling back to
an English Profile language. Display genre labels localize without changing the
canonical genre, Spotify query, frozen mix or opaque action identity. Active
GET query language and ordinary hybrid read payload.language share the existing
handler; locale projection uses a safe authored fallback without generation or
renewing leases. Watch never receives the extra For-you card or continuation.

A non-replayed, accepted Settings3 Mood revision schedules one bounded server
preparation. Same-revision replay, reconnect and polling never schedule another.
The original owner/source/pairing/Session/settings/DNA/history guards remain;
late results cannot replace a newer Mood offer. A failed revision stays failed,
and an in-flight or uncertain explicit effect blocks automatic replacement.
refresh_request.automatic remains false; refresh_policy is server-owned status.

Selection and readback retain the actual admitted speaker result/context in
continuation. Its outer and nested result-set TTL only decrease against the
original wall/monotonic lease. The original mood revision remains bound; stale
speaker actions disappear. One explicit genre then speaker selection starts the
same mix; a duplicate speaker turn never repeats the effect. Unknown dispatch
is never silently upgraded or retried. Manual explicit renewal remains available
through the existing owner, without retaining a stale output continuation.

The existing explicit Session-start mood is a Session-only welcome choice.
Missing choice and internal automatic starts retain canonical defaults. The
stored Profile defaults and defaults_revision do not change because of the
welcome preview/start choice; no post-response correction write is invented.

Validation on qualified product commit `9bfd10d3`:

- 27 isolated actual HA protocol harnesses pass with unchanged before/after
  product hashes;25 current receipt projections bind308 product files.
- Eight new real paired HTTP/Settings3/SQLite cases pass in EN/NL: explicit
  Session-only start against different defaults, one refreshed offer without
  playback/retry, original speaker continuation/lease, and exact mix once with
  duplicate-request protection.
- 419 related tests pass in their existing isolated fixture lifetimes;
  29 source/harness receipt checks pass. Four additional owner-suite filenames
  are scheduled before any provider work by the existing release matrix runner.
- Ruff, diff, planning and lifecycle checks pass. Original failure logs remain
  preserved; no historical raw receipt or old outcome is rewritten into PASS.

The [actual HA wire fixture](../../examples/client_contracts/session_for_you_v1/actual-ha-mood-refresh-20261106.json)
contains exact EN/NL examples and hashes for Apple decoder/component tests.
External provider/model replies and accounts are declared synthetic. No real
Spotify/model calls, installed-HA change, native UI/provider/audible/APNs or
complete editorial qualification is claimed. Source CI, protected merge,
Finalization, any installation and physical acceptance remain separate gates.
