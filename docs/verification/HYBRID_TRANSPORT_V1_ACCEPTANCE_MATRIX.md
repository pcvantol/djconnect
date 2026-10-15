# Hybrid transport acceptance matrix v1

Assignment DJC-CORE-HYBRID-TRANSPORT-CONVERGENCE-V1-20261013. All new rows start
NOT_RUN; historical Apple40021 PARTIAL evidence is not current acceptance.

| Boundary | Positive proof | Negative/race proof | Initial status |
| --- | --- | --- | --- |
| Paired origin/auth | Real paired identity on validated TLS and first-frame auth | Relay/wrongcertificate/plaintext,wrongtoken/retiredclient,Profilechange | NOT_RUN |
| Action parity | Actual HTTP/WS same application handler/result/revision | Unsupported operation,identity override,authoritative rejection | NOT_RUN |
| Correlation | Concurrent out-of-order IDs/results,one reader | duplicateID,cancel,late reply,socketreplacement,queuefull | NOT_RUN |
| Receipts | Same ID acrossWS/HTTP invokes domain/provider once | conflict,expiry/GC→clockrollback/restart,capacity,oldboot,Storefail | NOT_RUN |
| Dispatch boundary | Qualified result and real effect count | before/after provider send/local commit,cancellation/crash | NOT_RUN |
| Private data | Current owner/no-store/response rights | source/Profile/token withdrawal,expired grant,recovery leakage | NOT_RUN |
| Quiet liveness | Real ping/pong and lease renewal | half-open,Off/pause,noevent,suspension,end | NOT_RUN |
| Broadcast HTTP recovery | Existing cursor/watermark/DTO projection | gap,snapshot_required,expiry,no duplicate publication | NOT_RUN |
| Routing producer | Authenticated install identity/metadata contract | wrongorigin/redirect/TLS/absentexternal | NOT_RUN |
| Native automatic routes | Apple-owned Mac/iPhone/iPad live route coordinator | LAN→cellular→LAN/foreignWi-Fi/background,requests/cost/battery | OPEN_APPLE |
| Regression | Presence/Mood/Forecast/history/summary/sharedAskDJ/drilldown | selection/clear/revision/source races andoldHTTPclients | NOT_RUN |

Use genuine isolated HA/router/auth/Profile/Runtime/Store/Broadcast and real
HTTP/WebSocket sockets. Only external music/speech/model boundaries may be
explicit fixtures. Measure latency,requests,peak resources and executioncounts.
A producer software PASS does not promote native/installed/hardware/joint status.
Independent technical/concurrency/security and product/network-UX reviews must
qualify the exact final candidate after fixes. No deployment/installation here.

## Explicit consumer-context chains

- Chosen catalog A → qualified route change → explicit Play stays exactly A;
  no re-search, selection loss or extra effect. Original deadlines remain.
- Confirmed private answer → body loss/expiry/restart retains confirmed phase,
  result_available:false, no automatic regeneration/model cost.
- Expired selected source chip is withdrawn without destroying a local draft;
  history paging/search/scroll position remains consumer-owned and stable.
- Unproven LAN, wrong TLS identity or failed reachability does not delete pairing,
  Profile/history or an authorized Session. Only authoritative authenticated
  revocation/profile/source denial withdraws the corresponding private view;
  leaseexpiry alone reconnects and does not mean pairingrevocation.
- A relayed valid standalone challenge is never accepted as channel identity;
  server certificate/hostname/pinning validation precedes token release.

Early design454a470f is not runtimeGO: independent reviews rejected its standalone
HMAC-origin assumption and missing rollback fence/phase-content distinction.
Those findings are corrected before corresponding runtime implementation.

## Connected preliminary checkpoint

`tests/fixtures/hybrid_transport_v1.json` records 17 actual isolated HA/TLS/WS
transport cases from the exact source hashes it embeds. Ordinary pairing,
validated local TLS, first-frame paired actions, canonical active Session,
HTTP snapshot-required recovery, HTTP/WS operation dedup, two deliberate skips,
payload conflict, audience rejection, request-ID reuse rejection and journal
reopening pass. Exactly two external provider mutations occur; no model calls.
No installed or native result is inferred. This is `PASS_CORE_TLS_HA_BASELINE`,
not completion of the matrix above. Full operation parity, withdrawal/race,
backpressure, liveness, resource and final independent reviews remain required.

Fourteen journal/service owning units additionally cover cancellation, uncertain
Store acknowledgement, revoked authority, slow-save expiry and original
owner delivery guards. These are unit evidence, distinct from actual HA sockets.
