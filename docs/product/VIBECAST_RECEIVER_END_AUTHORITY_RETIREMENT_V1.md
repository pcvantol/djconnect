# VibeCast receiver end-authority retirement v1

The [web-first experience](VIBECAST_WEB_FIRST_EXPERIENCE_V1.md) makes the shared
screen readonly. The owner's 17 October 2026 report of the remaining HA checkbox
requires retiring its entire end-authority path in the current Core correction.
This is the bounded current-main delivery of an already selected correction; no delivered/installed claim until exact candidate gates pass.

## Behavior and compatibility

- Remove `vibecast_session_end_allowed` from the voice form, defaults, accepted
  submissions and all five language catalogs. Existing stored values are inert;
  normal settings save drops them without changing other settings or pairing.
- Remove receiver grant issuance, grant storage, expiry/revocation machinery and
  the `end_grant` handoff field. Ordinary authenticated handoff retains its
  existing Profile, exact active Session and entry-lifetime authorization checks.
- The old `POST /api/djconnect/v1/session/broadcast/control/end` is a compatibility
  tombstone: HTTP410, `vibecast_end_control_retired`, `Cache-Control: no-store`
  and `Referrer-Policy: no-referrer`. It never parses the request, validates a
  credential, reads a Session or changes state. Old grants cannot be upgraded or
  used; malformed requests and unknown Session IDs reveal no Session information.
- Remove the generated renderer's end button, translations, handler and request.
  An injected old handoff grant is ignored. Screen close and share close remain
  separate from ending the Session. A genuine server-side Session end still
  renders the normal idle state.
- Preserve the paired owner Session-end route and existing persistence rules.
  Preserve generic entry-generation and unload/subscription invalidation through
  `async_invalidate_receiver_entry`; no authority survives a revoked entry.
  These fences serve other owners and are not dead end-grant machinery.

No store rewrite, Profile reassignment, Session termination, new authority type,
receiver write or Swift change is required. Historical receipts remain intact.

## Consumer boundary

Read-only code inspection finds no end-grant consumer in Apple or Pi. The existing
Core Cast host already excludes end authority from forwarded handoffs. The
receiver repository still contains the old imported HTML handler and historical
negative tests. Its later renderer import belongs to that lane. A cached older
screen may retain its button until refreshed, but the retired Core endpoint
cannot terminate a Session. No consumer deployment or native acceptance is
claimed by Core source tests.

## Qualification

Owning tests cover removed form/save fields, stale true/false values, handoff
serialization, absence of Runtime end-grant APIs, normal owner end, non-Spotify
Session preservation, and unload/pending-subscription fences. Node renderer
contracts and a portrait/landscape browser fixture verify no end control or
request, ignored legacy handoff input, and genuine server-end projection.

The network-isolated HA probe uses normal device pairing, Session start,
owner-authorized handoff/collection and Broadcast GET. Old-grant, Broadcast-token,
missing, unknown-Session and malformed requests must return410 while the active
Session and Broadcast remain identical; normal paired owner end must then work.
It performs zero model calls and zero provider playback mutations. Provider
fixtures are external I/O only. This is isolated HA/software evidence, not a live
HA-dev/prod or physical-screen result.

The source, exact independent review, protected delivery, Finalization and
installed readback remain part of the existing corrective assignment. Broader
personal narrative quality remains open and is not closed by this retirement.

Historical local qualification on e2456029 (not current-main delivery evidence):255 targeted tests,2,272 host regression tests with
seven existing skips, 173 DAG tests, reproducible local/static renderer build,
and eight portrait/landscape browser captures passed. The paired HA probe passed
all five obsolete end-request variants and preserved normal owner end, with zero
model calls or playback mutations. Independent technical/privacy and product/UX
reviews gave scoped GO; the added current-inventory hash keeps the historical
settings-delivery receipt byte-equivalent. These results do not grant broader
narrative quality, release, installed, native or physical-screen acceptance.

## Current-main delivery boundary

The standalone correction is based on0adaef7d and contains only this retirement.
The original Profile settings inventory remains a dated148bd5ae source census
with its historical delivery hash unchanged. Its earlier
ACTIVE_LEGACY_AUTHORITY_REMOVAL_REQUIRES_DEPENDENCY_QUALIFICATION disposition
for `vibecast_session_end_allowed` is superseded by this contract and the current
source/tests. This is not a roaming setting or remaining receiver end authority.
No other inventory disposition, DAG node/status or historical receipt changes.

Current tests and exact candidate pins are recorded in the separate [delivery qualification](../verification/VIBECAST_END_RETIREMENT_QUALIFICATION_20261017.md); historical e245 results above are not reused as current PASS.
The broad personal-DJ quality NO_GO and other consumer gates remain open.
