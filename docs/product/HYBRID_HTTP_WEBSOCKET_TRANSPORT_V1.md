# Hybrid HTTP/WebSocket transport v1

## Forward local-transport refinement

[Qualified direct local HTTP/WS policy v1](HYBRID_LOCAL_TRANSPORT_POLICY_V1.md)
supersedes the TLS-only admission statements below exclusively for a proven
direct local ingress. External/proxy access still requires authenticated TLS.
No global downgrade or native/installed acceptance follows from this design.
The original TLS-only baseline remains documented below for historical and
legacy-client behavior; all operation, identity and privacy semantics remain.

Assignment: `DJC-CORE-HYBRID-TRANSPORT-CONVERGENCE-V1-20261013`;
[selection6149934177](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6149934177),
ACK6185332170. Contract-first design, not an advertisement of unfinished routes.
Admission main9efd1977768d2574b66c16de9c5d8ba53e9157b1, sole Core writer.

## Ownership and baseline

One Session Runtime, Planner, shared Ask DJ service, TrackInsightService and music
command owner remain. Transport authenticates, correlates, bounds and routes;
it does not plan music or reconstruct conversations/history. The original
`active_owner_broadcast` audience remains subscribe/recover only. Native HA
`/api/websocket` retains HA authentication; no HA credential issuer is introduced.

The historical Apple40021 audit in its existing writer's recovery directory is
PARTIAL, sourceffc65884 plus WIP, not current installed evidence. It reports a404
issuer, undemultiplexed optional action replies, ambiguous mutation retry and
missing quiet-socket liveness. Source fixes and497 tests/builds belong to that
writer and are not rerun or claimed by Core. Actual Apple root2fc7fdf plus WIP
is preserved; remote main446ff156 is distinct. Apple consumer admission is separate.

### KEEP/REUSE/FIX/RETIRE inventory

| Existing family / owner | Local v1 preference | External | Effects/cost/identity and disposition |
| --- | --- | --- | --- |
| Pairing/configuration / existing pairing owner | HTTP | Trusted HTTPS | KEEP; no reset or token issuer; configuration mutation never retried speculatively. |
| Capabilities / shared declarations | HTTP discovery | HTTPS | REUSE; flags only after connected positive qualification, not a grant. |
| Active Session / existing active handler | Paired action read, HTTP fallback | HTTPS | REUSE; owner/Profile/no-store; no new Runtime or provider fetch. |
| Start/end / existing lifecycle handlers | HTTP operation envelope | HTTPS same envelope | REUSE; Session identity and authorization unchanged; receipt/CAS, not blind retry. |
| Mood/presence / existing CAS handlers | Paired action, HTTP same owner | HTTPS | REUSE; independent revisions and existing race/off/in-flight rules. |
| Broadcast/Moments/Forecast | Existing paired Broadcast; owner HTTP recovery | HTTPS recovery | REUSE/fix liveness; watermark/cursor distinct from Flow sequence. Source expiry/native admissions unchanged. |
| History/search/open/summary / query owner | HTTP | HTTPS | KEEP HTTP-only paging; no client counting/N+1 or WS private-history replay. |
| Ask DJ text / shared exchange | Paired action or HTTP operation | HTTPS operation | REUSE; same client_message_id and receipt; one generation/acceptance; no transport-owned history. |
| Voice/STT/raw audio / existing voice route | HTTP-only | HTTPS | KEEP uploads; no binary/base64 WS; after-send timeout is unknown, never automatic reupload/model replay. Shared post-STT exchange remains owner. |
| Raw Ask DJ / existing shared compatibility | HTTP-only | HTTPS | KEEP compatibility; no automatic after-send retry without qualified exchange identity. |
| Ask DJ history/clear / history owner | HTTP | HTTPS | KEEP revision/clear rights; nonrepeatable clear cannot fall back after rejection/uncertain send. |
| Playback/result/output choices / command/shared exchange | Limited paired action, same HTTP operation | HTTPS operation | REUSE actual command handler; relative/toggle/queue actions require one immutable operation identity per deliberate action. Selection never implies Play. |
| Track Insight/drilldown / TrackInsightService | Paired action or HTTP operation | HTTPS operation | REUSE exact target; generation is not a harmless read. Never substitute B for target A. |
| Music DNA/profile/settings/clear/export/import | HTTP-only | HTTPS | KEEP opt-in, retention, revision and export/import scopes. No new management product; no automatic uncertain mutation retry. |
| Discover/feed/refresh/play/feedback | HTTP-only | HTTPS | KEEP generation/source/rights boundaries; refresh may cost, play mutates; never automatic after-send replay. |
| Images/TTS/audio/art/export files | HTTP-only original managed resources | HTTPS | KEEP grants/provenance/expiry; no private grant copied into Broadcast or VibeCast. |
| Optional native HA action adapter | Existing HA auth only | No new dependency | RETAIN compatibility, same domain handlers; old broad catch→HTTP rule RETIRED. |
| `/websocket/session` issuer expectation | Not supported | Not supported | RETIRE consumer expectation, never restore an HA credential issuer. |

Detailed live route inventory remains docs/technical/inventory/http_routes.json
and websocket_commands.json; this family matrix defines supported migration,
not a claim every existing native HA command belongs to the new paired audience.

## Route authority and transitions

Apple owns one shared coordinator for Mac/iPhone/iPad: local-ready,
local-degraded, remote-ready, recovering/offline, terminal-authority-withdrawn.
Wi-Fi/Ethernet is a hint, not proof of this HA installation. Use configured trusted
origins and existing TLS policy; never follow cross-origin redirects with secrets.
The new paired action and operation routes require authenticated HTTPS/WSS with
normal certificate/hostname validation or an explicitly existing pinned HA identity.
Never release a paired secret because a public capability, interface, HTTP200 or
challenge response looked plausible. A relay can forward a valid HMAC challenge;
a standalone HMAC probe does not bind the subsequent channel and is rejected as
authority. No new probe/token-issuer route or replacement cryptographic channel.

An owner-authenticated transport-context read on that protected channel returns
version1, stable existing ha_install_id, server epoch/time and supported policy.
The expected installation is retained from ordinary pairing; identity mismatch
withdraws that route without trying another account. No read creates a new
installation ID or changes endpoint configuration. A missing legacy install ID is
unqualified until the existing authorized setup lifecycle supplies it.

Local cleartext HTTP is retained legacy compatibility, not proof for a new
sensitive automatic fast path on foreign networks. HTTPS/WSS-positive local
qualification is required; do not declare completion from universally disabling
local actions. Apple must qualify its existing configured/pinned local HTTPS
route, or report the affected plaintext-only installation subset OPEN rather
than weaken server identity or send secrets to an unproven LAN address. Core
provides working TLS-positive sockets and rejects insecure new action/operation
requests; it does not install a proxy, certificate, service or global trust rule.

After confirmed remote readiness, share one probe and bounded backoff/hysteresis;
do not pay full LAN timeout per request. Foreground/network change triggers a
bounded reassessment, not a new Session, history clear or playback transfer.
Missing external URL is an honest offline/configuration state, never a fabricated
endpoint. Consumer defaults automatic routing; optional diagnostic override is
bounded and not a permanent normal-use checkbox. Existing explicit settings need
an Apple-owned migration and visible fallback guidance in all five languages.

## Separate paired action adapter

New relative path `/api/djconnect/v1/actions/paired`, protocol1, audience
`paired_owner_actions`. On the authenticated TLS channel, same paired first-frame identity/secret as Broadcast,
5s auth deadline,300s connection lease,1s revocation checks, no HA token. Never
silently add commands to Broadcast v1. Allow only declared domain operations.
Session/owner/Profile resolve server-side and are revalidated before acceptance,
private result delivery and actual provider dispatch. Shared rooms, retired Windows,
Pi/Cast/TV and guest renderer credentials do not acquire action grants.

One reader, request-ID demultiplexing and one bounded writer queue. At most8
outstanding commands,64 queued responses,64KiB text frame and256 distinct IDs per
connection. IDs are positive integers and cannot be reused on that connection;
`connection_id` changes on replacement and accompanies results. Register pending
request before send; replies/events never share positional receive assumptions.
Heartbeats use WebSocket ping/pong; no Moment/pause/presence-Off is not failure.
Heartbeat15s, bounded pong deadline; reconnection before/at300s lease does not
rotate pairing, operation epoch, Session or receipts. Background limits remain
platform-owned, not an unlimited polling promise.

Commands: `djconnect/read` for qualified declared pure projections,
`djconnect/operation/execute` and `djconnect/operation/status` for the closed
operation policy. Reads use the same handlers; uploads/paging remain HTTP-only.
Command semantics and restart/uncertainty are in the operation recovery contract.
Additive hybrid_transport capability metadata describes implemented paths and limits;
it never authorizes a URL, token release or native acceptance.
Server advertises only implemented operation/version sets after real qualification.

Server allocation is bounded to16 action connections in total (including the
5s unauthenticated window), and2 authenticated action connections per paired
device. The second slot permits replacement/reconnect overlap; close the old
socket once the new one is authoritative. A capacity rejection is transient,
never proof that pairing or Profile was revoked. Native requests normally omit
Origin; a supplied browser Origin must match this exact HTTPS origin. Foreign,
opaque or malformed browser origins are rejected before reading credentials.
No cross-origin redirect or certificate-validation bypass is introduced.
Connection close codes distinguish authority rejection from transport/protocol
loss. `auth_timeout`, `auth_expired`, `slow_consumer`, `connection_capacity`,
`invalid_request_id` and `invalid_projection` never by themselves revoke stored
pairing. A post-auth send timeout is `slow_consumer`, not invalid credentials.
Only a qualified authenticated owner/source rejection withdraws its authority.

## Recovery and consumer acceptance

Owner HTTP recovery must use the existing Runtime/Broadcast recovery owner,
not a second timeline. A bounded owner POST recovery projection may expose the
same cursor result without a retained subscription. Replay returns only qualified
currently deliverable events; snapshot_required is an honest coverage gap, not
proof that every missed Moment was rendered. The TLS-only owner POST is
`/api/djconnect/v1/session/broadcast/recovery` with closed JSON
`contract_version:1`, `identity:{device_id,client_type}`, `session_id` and the
original opaque `recovery_cursor`, using ordinary paired bearer/device headers.
The same read is available as `session/broadcast/recover` on paired actions.
Never replay expired/inaccessible
cards or count transport deliveries as new publication.

Apple receives an exact source/schema pin and real transport fixtures early.
Its existing writer owns automatic routing, request demux, retained drafts/scroll,
no-known-Session discovery, view withdrawal and actual Mac/iPhone/iPad behavior.
Native/installed LAN→cellular→LAN, foreign Wi-Fi, suspension and lease renewal
remain OPEN until separately authorized actual evidence. Core producer completion
does not close the joint capability. Artwork remains the next separate slice.
