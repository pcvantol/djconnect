# Hybrid transport acceptance matrix v1

Assignment DJC-CORE-HYBRID-TRANSPORT-CONVERGENCE-V1-20261013. All new rows start
NOT_RUN; historical Apple40021 PARTIAL evidence is not current acceptance.

| Boundary | Positive proof | Negative/race proof | Initial status |
| --- | --- | --- | --- |
| Paired origin/auth | Real paired identity, challenge and first-frame auth | Foreign host/challenge,wrongtoken/retiredclient,Profilechange | NOT_RUN |
| Action parity | Actual HTTP/WS same application handler/result/revision | Unsupported operation,identity override,authoritative rejection | NOT_RUN |
| Correlation | Concurrent out-of-order IDs/results,one reader | duplicateID,cancel,late reply,socketreplacement,queuefull | NOT_RUN |
| Receipts | Same ID acrossWS/HTTP invokes domain/provider once | conflict,expiredID,capacity,oldboot,Storefail | NOT_RUN |
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
