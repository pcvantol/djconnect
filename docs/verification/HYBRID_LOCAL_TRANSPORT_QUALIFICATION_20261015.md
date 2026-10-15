# Direct local HTTP/WS software qualification — 2026-10-15

Assignment `DJC-CORE-HYBRID-LOCAL-HTTP-WS-FIX-V1-20261015`; same sole Core
writer, base62c8156db376c679eb636a7c8ff4d088276632e9,
branch `codex/hybrid-local-http-ws-v1`. First contract38450dc0 precedes first
runtimeb07b6338. Previous iPad500 source1178/Finalization1179 is closed;
Speech1177/head533fa48c and other WIP remain preserved.

## Actual software chain

[Qualified policy](../product/HYBRID_LOCAL_TRANSPORT_POLICY_V1.md) is implemented
once for all four hybrid HTTP adapters and paired WS. Global TLS legacy flags
remain conservative; only a successfully authenticated request-qualified context
reports direct local HTTP mode. Existing auth, Profile, installation identity,
operation service/journal, domain dispatch and delivery fences are unchanged.

[Real transport fixture](../../examples/client_contracts/hybrid_local/qualified-runtime.http.json)
and [measurement summary](../../examples/client_contracts/hybrid_local/qualification-summary.json)
record66 actual isolated HA2026.10.0 cases. Ordinary pairing, Session Runtime,
HTTP context/operation/status/recovery, WS first-frame authentication, current
Session read, reconnect and original-ID status/duplicate execution use real Core
owners and storage. Only external music/source I/O is a fixture. Direct local
positive ingress is real loopback plus existing HA internal URL configuration;
it is explicitly not a physical LAN test. Existing TLS-positive and certificate,
audience, access/source-revocation, capacity, frame, failure/restart/expiry and
Session-end cases are retained. Foreign Origin and proxy headers reject both
HTTP and WS before auth. Every hybrid HTTP entry rejects forwarded plaintext.

Exactly four deliberate provider mutations remain four; local duplicate/reconnect
and status reads add none. The new local status operation also reuses its original
identity without extra provider queries. Zero real model calls. No provider
exactly-once guarantee is introduced. All167 integration/verifier/helper file
hashes in the fixture match current bytes; documentary descendants change none.

Actual idle lease300.012s; missing-pong close23.014s; auth deadline5.011s;
idle source withdrawal1.007s; token rotation1.004s. Real maximum RSS223124KiB
inside the1GiB/2CPU/256PID networkless owned container. Journal17048bytes before
idle expiry,879bytes after expiry/GC. These measure this sample, not an absolute
peak storage claim. Own containers remove themselves; shared HA/Apple labs,
provider configuration and installed environments were not changed by these tests.

## Regression and coverage

1957tests run,1950pass,7existing skips.31owning security/journal/service units
PASS. Combined branch-aware units plus real HA coverage89.62%: new pure ingress
policy100%, capability100%, service88.70%, HTTP/WS adapter87.23%. Actual isolated
HA coverage is combined using source-path mapping, not relabelled unit evidence.
150DAG tests, capability snapshots, schema/reference/generation,13bootstrap/
lifecycle tests, offline governance projection, Ruff and onboarding package
freshness pass. Existing nodes, edges, receipts and historical snapshots remain;
only current document references and generated source views change.

## Explicit remaining boundaries

Current HA-dev Docker peer/config cannot qualify the requested physical LAN
path: observed socket peer192.168.65.1, container interface172.18.0.2 and no
configured internal URL. No private-gateway exemption or forged Host/Origin/XFF
workaround is introduced. Ingress/topology evidence preserving actual locality
is required separately; no proxy, certificate, firewall or service change occurs
in this Core repair. Source software success does not establish installed/native
LAN, LAN→cellular→LAN, widgets/Speech, physical hardware or joint acceptance.

This candidate remains LOCAL/UNPUBLISHED until exact independent review and its
own valid publication/protected delivery gates. Current installed dev/prodmain62c
contains the previous iPad500 repair, not this new local transport implementation.
Apple receives an exact producer/schema/fixture pin under its existing writer;
no Swift writes, new consumer admission or native PASS is inferred. Separate
Finalization and safe own cleanup remain required after any source delivery.
