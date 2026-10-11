# Windows client retirement v1 — Core qualification

Assignment: `DJC-CORE-WINDOWS-CLIENT-RETIREMENT-V1-20261011`.
Source base: `0b4c941bfb0a129facafc86ea4e94bca96bb96db`.
Sole branch: `codex/windows-client-retirement-v1`.
ACK: Core #1101 comment6106248916; first material policy record6106305126.
Decision: software candidate qualified; protected delivery and Finalization pending.

The [disposition contract](../product/WINDOWS_CLIENT_RETIREMENT_V1.md) was
recorded before producer changes. Windows app identity is recognized only for
legacy quarantine; it is removed from supported configuration, pairing and
device authentication. Explicit retired or unknown identity cannot fall back
to Apple. Apple, Pi, ESP and Assist retain their distinct existing contracts.

## Before and after

Committed sanitized receipts, source hashes and genuine HA screenshots are in
`examples/client_contracts/windows_client_retirement_v1/`; `manifest.json`
pins every evidence file. The current integration payload digest is
`87a13f5f9cb340ae6c1edeeed4bdc9db4db883ce4bfb574f3dfca2e70f856b2e`:
134 integration source files, independently checked with zero differences.

The immutable base, real HA configflow/router/ConfigEntries/Store and synthetic
configuration captured ten baseline receipts: Windows was offered in five
languages, ordinary Windows pairing minted a persisted token and changing or
omitting the client type could still authenticate the retired runtime.
Seventeen current ingress receipts prove refusal through the actual router,
options manager and flow, including the genuinely minted old token, nested
identity and type/prefix spoofing. No HA user credential replaces device auth.

The native HA2026.10.0 frontend20260930.2 was run from pinned image
`sha256:1b64d38f38d922bf9d59336451fd6453e1d614f934456af4ee3d2a51061be3a4`
in an own bounded internal-network container. Five-language before/after
wizard screenshots show the supported Apple choices and Windows removal.
Actual HA Repair-registry screenshots show distinct retained-connection and
safe-to-remove states, each naming the synthetic configuration. The local
synthetic HA UI user only opens these native dialogs; it is not transport proof.
Profile reuse and duplicate-name recovery also pass the actual FlowManager,
without creating a new Profile or OAuth connection.

## Legacy ownership, persistence and recovery

58 real-HA provider receipts qualify the bounded v1 disposition. Their SHA256 is
`959df2ba071a7afa8d30f7dc6201741f884833a941d1ad25358af789a8722d75`.
They use actual HA Store, server-owned Profile/account bindings, SessionRuntime,
SQLite archive, pairing router, HTTP and paired websocket handlers. The fixture
never sends a provider-cloud request and creates no extra HA user credentials.

A retired entry loads as provider-only quarantine with visible management
feedback. Exactly one already-bound healthy retained peer can take over only
the same existing provider connection. Device identity/token are unchanged;
historical row bodies and captured account attribution are unchanged. The real
HA manager removes the retired entry after the handoff; retained Apple then
passes timeline/search/Ask DJ history and ordinary pairing-token
auth → snapshot → Runtime update.

The matrix includes real committed-stage cold recovery, unloaded/disabled
followers, idempotent disk readback, ambiguous/conflicting/revoked bindings,
stale cached backend authority, Profile/account/runtime withdrawal at each
saved stage, concurrent OAuth changes during both forward writes and rollback,
new donor references arriving during lock acquisition or saved stages,
readback failures and cancellation while the real physical Store writer is
pending. Recovery preserves concurrent management changes and replays their
normal update listeners. Synthetic SQLite backup restores only independent
test fixtures; it is not a producer authority or production recovery path.

HA2026.10 removes ConfigEntries before callbacks and swallows callback errors;
an exception cannot veto deletion. Its existing Store also uses non-atomic
writes and may swallow write errors. The bounded adapter uses that manager's
single existing writer and verifies completed disk content; unavailable
boundaries fail closed. This is not a claim of power-loss atomicity. An
unresolved donor remains quarantined with a retained-connection Repair;
arbitrary forced deletion of that configuration is not preservation-safe.

## Checks and independent review

- Canonical unittest: 1,692 tests, seven existing skips, PASS.
- Pytest `tests/`: 1,897 passed, seven skipped, 906 subtests, PASS.
- Actual paired-live regression: 57 receipts, faults/reconnect/rotation and the
  unshortened 300-second lease expiry, PASS.
- Ruff, required medium-severity Bandit and committed AI-development projection
  validation: PASS. No dependency, workflow, release version or runner change.
- Combined unit/real-HA coverage for the retirement helpers and provider
  resolver: 87%; client retirement92%, provider resolver89%, handoff86%.
- Shared local/static renderer builds and pinned manifest verification: PASS;
  renderer bytes and Cast1.1 semantics unchanged from the source base. No new
  browser or physical renderer acceptance is claimed by this slice.

Independent read-only technical/privacy review challenged and resolved
listener ordering, durable readback, cancellation, current authority, concurrent
grant preservation and late-reference recovery. It confirmed the current
134-file pin and 58 receipts, with no remaining findings. Independent UX review
qualified all five native wizard/Repair locales, named states and current
support documentation, with no remaining findings.

The fresh canonical hostverify is MATCH, onboarding4.5.3, exit0. A test-created
88-byte default YAML copy inherited the template's old timestamp; only that
own generated copy was preserved outside the checkout and removed from the
retention inventory. Existing lab storage and other installations were retained.
Subsequent full tests use an own verification-output root.

## Delivery and remaining ownership

| Outcome | Current qualification |
| --- | --- |
| `CORE_WINDOWS_CLIENT_REMOVAL` | PASS — candidate software and actual native HA wizard |
| `LEGACY_CONFIG_COMPATIBILITY` | PASS — bounded v1 synthetic HA disposition/recovery; unresolved donors remain quarantined |
| `RETAINED_CLIENT_REGRESSIONS` | PASS — software contracts and ordinary paired Apple live/history |
| `INSTALLED_ACCEPTANCE` | NOT_CLAIMED — no existing HA installation updated |
| `WINDOWS_INFRA_RETIREMENT` | NOT_IN_SCOPE — parent Windows #76 remains open |

Source and Finalization each retain their exact publication grant. Finalization
will record the two PRs, exact main/artifact readback, rolling records and own
workspace cleanup. Windows #76 receives the exact Core handoff and owns the
remaining repo/runner/CI/website/distribution/VM/.NET inventory and approvals.
No real HA config/token, Apple/native source, receiver, Pages, hardware or
infrastructure effect occurred. No follow-on capability is started.
