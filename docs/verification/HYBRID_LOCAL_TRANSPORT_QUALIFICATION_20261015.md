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
record68 actual isolated HA2026.10.0 cases on runtime checkpoint
1474907711ef6b3f2ab4017963a1c357fcefa714. Ordinary pairing, Session Runtime,
HTTP context/operation/status/recovery, WS first-frame authentication, current
Session read, reconnect and original-ID status/duplicate execution use real Core
owners and storage. Only external music/source I/O is a fixture in that chain.
Direct local positive ingress uses a lab-only operator qualification record bound
to the actual installation/interface/origin, allowed127.0.0.2 and excluded127.0.0.1,
plus real loopback sockets and existing HA internal URL configuration;
it is explicitly not a physical LAN test. Existing TLS-positive and certificate,
audience, access/source-revocation, capacity, frame, failure/restart/expiry and
Session-end cases are retained. Foreign Origin and proxy headers reject both
HTTP and WS before auth. Every hybrid HTTP entry rejects forwarded plaintext.

Exactly four deliberate provider mutations remain four; local duplicate/reconnect
and status reads add none. The new local status operation also reuses its original
identity without extra provider queries. Zero real model calls. No provider
exactly-once guarantee is introduced. All168 integration/verifier/helper file
hashes in the fixture match current bytes; documentary descendants change none.

Actual idle lease300.002s; missing-pong close23.137s; auth deadline5.007s;
idle source withdrawal1.001s; token rotation1.007s. Real maximum RSS248292KiB
inside the1GiB/2CPU/256PID networkless owned container. Journal17762bytes before
idle expiry,879bytes after expiry/GC. These measure this sample, not an absolute
peak storage claim. Own containers remove themselves; shared HA/Apple labs,
provider configuration and installed environments were not changed by these tests.

## Review-driven security corrections

Earlier920/b2/658 candidates received technical NO_GO and are superseded;
their earlier receipts are not current acceptance. First, loopback/subnet alone
could not exclude a headerless proxy/SNAT route, so explicit deployment
qualification and exact peer exclusions were added. The actual HA chain now
rejects a headerless127.0.0.1 proxy forwarding valid credentials and matching
Host/Origin. Removing the administrative file while an operation waits at the
external provider boundary produces route withdrawal with zero extra provider
calls/mutations. No current installed Docker gateway is admitted.

Then review found final-await gaps. Ordinary paired authorization now rechecks
the existing synchronous owner/Profile/source/grant/entry-generation fence after
the last ingress await, alongside a non-yielding record-metadata/expiry check.
HTTP/WS private delivery rechecks after admitted-body awaits; the existing final
effect fence rechecks after Ask DJ turn guards. Five auxiliary race units cover
owner revocation during ingress await, record withdrawal during owner resolution,
delivery withdrawal/expiry and the final Ask DJ guard. These authority/dispatcher
fixture units run in the HA image but are explicitly separate from real pairing/
operation acceptance. Their script hash is recorded separately in the summary.

## Regression and coverage

1964tests run,1957pass,7existing skips.38owning security/journal/service units
and5auxiliary race units PASS. Combined branch-aware units plus real HA coverage
91.57%: pure local policy100%, operator qualification98.63%, capability100%,
service88.48%, HTTP/WS adapter89.53%. Coverage combines current path-mapped
measurements; dynamic-import units are traced by source file path. Actual isolated
HA coverage is combined, not relabelled unit evidence.
154integrated DAG tests, capability snapshots, schema/reference/generation,13bootstrap/
lifecycle tests, offline governance projection, Ruff and onboarding package
freshness pass. Fresh hostverify reports MATCH/exit0/package4.5.3. Existing nodes,
edges, receipts and historical snapshots remain; only current document references
and generated source views change. Documentary source1181/Finalization1183 terminalmain
`f32b625eb0a3d1b8abfc2c81378d25d769c6766d` is now locally integrated. Its full
DAG/WEBschema2/decisions/receipts are retained; only document references are
united/refreshed. All168recorded runtime/verifier/helper hashes and the auxiliary
race-helper hash remain identical, qualifying reuse of the actual HA/coverage
measurements. Integrated document/schema/regression checks and exact independent
reviews are separately required before publication.

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
