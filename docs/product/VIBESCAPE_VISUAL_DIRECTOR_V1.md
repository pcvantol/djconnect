# VibeScape Visual Director v1

Core owns bounded visual interpretation and admission. The native Apple client
owns on-device speech recognition, microphone permission, rendering, random
composition, the scene, its revision, local dynamics bias and eight RAM undo
steps. An interpreted result is never an applied acknowledgement. VibeCast shared
displays remain read-only; this contract grants no microphone or playback action.

## Discovery and microphone help

Existing HTTP and WebSocket capabilities expose `vibescape_visual_director:true`,
contract version1 and a `vibescape_visual_director` object. Its closed `help`
contains eight stable example IDs and two scope phrases in exactly `en`, `nl`,
`de`, `fr`, `es`. The client places a localized help button beside its microphone. Every tap/open
fetches `GET /api/djconnect/v1/capabilities` afresh from the currently connected
server with local HTTP caching bypassed; the response is `no-store` and
`no-referrer`. Display only that fresh response's negotiated version1 catalogue
for the current locale. Bootstrap-cached capabilities, a bundled command list,
and older successful help responses are not fallbacks. Show loading, then
available/unsupported/error honestly. Cancel pending help reads on dismissal,
background, server/pairing/owner change; a generation fence rejects late results
from an earlier opening/context. A help fetch renews no visit or interpretation
lease and grants no microphone, STT, playback or Session authority. This is grammar
support, separate from OS microphone/STT readiness and current Session admission.
Do not enable recording from a capability boolean alone or use general Ask DJ
as an unsupported-command fallback. Hide this help when the contract is absent.

Dutch examples:

- Maak het rustiger en vloeibaarder.
- Maak het sneller.
- Meer diepte.
- Iets meer goud.
- Maak een variant.
- Hou deze stijl aan.
- Ga een stap terug.
- Terug naar de DJ.

A recognized scope phrase, such as “alleen dit nummer” or “zolang ik hier ben”,
selects `current_track` or `while_in_vibescape`; hold always uses the visit scope.
Unknown, mixed music/HA, inverse motion/fluid comparisons and ambiguous clauses
fail closed with422. This deterministic grammar is a bounded vocabulary, not
unrestricted natural-language or a model. No provider/model/tool fallback exists.

## Exact transport and authority

Paired iOS/macOS devices use authenticated JSON POST to
`/api/djconnect/v1/vibescape/context`, `/interpret`, `/revoke`. Existing device
bearer and identity must bind the already loaded entry, active owner Profile,
active Session, current backend/account/provider source and original observation.
No route learns a new pairing, creates storage or migrates a Profile/Session.
The closed versioned request/response schemas and examples live in
`examples/client_contracts/vibescape_visual_director_v1/`.

Bodies are at most8192 bytes, text1024 UTF8 bytes, opaque occurrence identifiers
256 UTF8 bytes. Duplicate keys, nonfinite values, unknown fields, malformed
UTF8, query strings and non-JSON/encoded bodies are refused. All responses,
including405, carry `Cache-Control:no-store` and `Referrer-Policy:no-referrer`.
No request body cache, transcript, exception text or success prose is retained.

Context captures authority before awaits and rechecks that original admission.
The first request may return503 until the existing Stage1 observation accepts
its next current sample; no extra provider or queue request is made for VibeScape.
Original Session/broadcast identity survives ordinary runtime value replacement.
Source/owner/authority-revision/lifecycle change rejects old work; returning to
an earlier source does not revive its admission. Both provider-error paths clear
visual metadata immediately, preserving the original visit budget.

An opaque observed occurrence changes on actually accepted track/output/seek
transitions. Output identity uses the exact device ID from that same existing
provider response, privately hashed; equal display names never merge devices.
An absent output ID makes the observation unavailable, without a name fallback.
No device ID or its hash enters the public context.
Freshness markers in observer/admission are content-free acceptance serials,
advanced only by an actually accepted Stage1 sample. They never retain the
previous projection or track metadata after expiry/revoke. Ordinary progress and polling do not create an occurrence. There is
no claim to detect an unobserved replay. Context lease lifetime is positive and
at most15seconds, shortened by original observation/visit expiry. Issued/expiry
are fixed; a newer poll never renews an old turn. Native must also measure the
original request-start monotonic deadline and absolute expiry, including STT
and network time. Observation metadata expires after20seconds without a fresh
accepted sample. Visit lifetime is the original30minutes with32 attempts total,
including rejected interpretation; track changes do not reset those bounds.

Interpret echoes original visit/turn/revision/occurrence/lease/expiry. Its closed
exclusive directive is `patch`, `undo`, `reset`, `variant` or `hold`, plus the
matching machine `effect_code`. Patch carries one RGB triple and/or motion,
depth, roughness, deformation; values must be finite0..1. Omitted fields are
preserved. `dynamics_bias` stays local and is never part of the patch. Client
cancellation, generation, revision and original expiry reject late responses.

Track changes clear current-track override and undo while preserving the visit
explicit-field mask. Hold promotes only explicit user fields, never the whole
generated baseline. Exit/background/owner/Session loss cancels native pending
work and clears local state; best-effort revoke cannot be required for local
invalidation. Core teardown withdraws before persistent lifecycle awaits.

## Privacy and qualification boundary

Only finite RAM admission/turn/tombstone/observation metadata is retained.
No transcript/audio/scene/reply/undo/seed persistence, history/DNA/Profile write,
Flow/Forecast/Moment publication, analytics, notification, general Ask DJ or HA
action results from visual interpretation. Full/unload/authority revocation
clears content and leases. Tombstones prevent immediate stale rearming and
bounded capacities reject new work rather than evicting live tombstones.

Synthetic pure/owner/SQLite cases and actual isolated HA registration/HTTP cover
the producer; see the verification record. Native microphone/STT, GPU, touch,
physical display and human visual acceptance require owning-client qualification.
No consumer adoption, installed release or user acceptance follows from fixtures.
