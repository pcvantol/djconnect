# Spotify requested versus provider-granted scope evidence v1

The owner explicitly requested targeted Spotify reauthorization when necessary
for current playback/playlist behavior. Live DEFAULT audit found all11 canonical
requested scopes, including playback modification and playlist reads, but no
persisted provider-granted evidence: the old callback records ctx.scopes rather
than token.scope. Requested is not granted. Preserve that distinction.

Before another same-scope PKCE consent flow, persist a bounded metadata receipt
from the actual successful token endpoint's scope field. It contains only schema,
status/source/observation time, validated scope names and public client-id digest;
never access/refresh tokens, code, verifier, authorization payload or raw response.
The canonical requested11 remain unchanged. No additional permissions are added.

A missing/malformed provider scope field means UNKNOWN; never substitute requested
names. New authorization-code grants replace the old evidence even when unknown.
A same-client ordinary refresh without scope preserves only a prior valid original
receipt, without renewing its observation time. A changed client cannot inherit
that receipt. Actual token rotation stays in the existing HA credential owner.
Config-flow, repair/options callback and ordinary refresh must propagate actual
metadata through their normal persistence owner. Do not reauthorize/refresh just
to create source-test evidence; qualification uses synthetic token wires only.

Diagnostics separately report requested and granted/unknown. Known insufficient
grants use the existing missing-scopes Repair. Legacy unknown evidence retains
existing requested-scope repair compatibility while explicitly reporting unknown;
it must not claim all scopes were granted. Scope metadata grants no execution,
pairing, enrollment, source-purpose or background rights and is not portable.

After source/CI/exact owner approval/merge and authorized HA-dev installation,
use the existing normal PKCE flow with the same11 scopes for DEFAULT to replace
unknown grant evidence. Human Spotify login/consent is handed off only if needed.
Tokens remain directly with HA. Read back the actual metadata and any missing
scopes; no playlist write/playback occurs as a scope test. Same-scope refresh or
reauthorization cannot remove independent Spotify app-mode/editorial restrictions.

This bounded fix is independent of the Ontdek context resolver/queue behavior and
parked retained-widget4 candidate. Separate source, protected merge/Finalization,
installed runtime, real OAuth grant and actual provider/native acceptance claims.
