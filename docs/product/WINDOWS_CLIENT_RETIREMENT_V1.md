# Windows client retirement — Core subset v1

Assignment: `DJC-CORE-WINDOWS-CLIENT-RETIREMENT-V1-20261011`.
Parent decision: `DJC-WINDOWS-RETIREMENT-V1-20261008`.
Admission base: `0b4c941bfb0a129facafc86ea4e94bca96bb96db`.
Source branch: `codex/windows-client-retirement-v1`.
Owner scope: https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6106139356

This inventory, compatibility policy and failing-scenario map precede producer
changes. They do not authorize installation or mutation of real user data.

## Active Core surfaces

| Surface | Current behavior | Required disposition |
| --- | --- | --- |
| `const.py`, `client_identity.py` | Windows is in supported and remote-capable client catalogues | Remove active support; retain its technical identifier only for legacy detection |
| `config_flow.py`, strings/translations | Windows has selectable app and details steps; invalid selection falls back to the default app | Remove selection/details copy in five languages; reject explicit retired/unknown input without default substitution |
| `__init__.py`, `request_auth.py` | Windows prefixes are accepted; request/runtime client type can rely on observed status | Deny retired device authority using server-owned entry identity even when request type or cached status is changed |
| `http.py`, `ha_urls.py`, `device_info.py` | Windows participates in app voice, remote URL and product naming | Remove active Windows capabilities; keep retained Apple/Pi/ESP/Assist behavior |
| Entry setup/unload/removal and `profile_backend.py` | A client entry can own the shared provider credentials; peers reference that entry | Retire client transport without deleting the existing Profile/account connection; preserve source binding and retained clients |
| `session_conversation.py`, history maintenance | History qualification depends on the captured provider entry; removal withdraws that source | Removing a retired client must not withdraw a still-retained shared account or rewrite historical Moments/flows |

Generic Windows operating-system support, onboarding tooling, old releases,
historical prompts and sibling repositories are outside this source slice.

## Minimum compatibility invariants

1. ConfigEntry schema version remains `1` unless verified migration needs prove
   otherwise. Retirement compatibility is explicitly versioned `v1`; recognition
   of `windows` is not continuing client support.
2. A legacy entry is quarantined from device pairing, authentication, discovery,
   polling, voice and client capabilities. It must not become Apple or an
   anonymous/guest actor. A visible five-language HA Repair explains retirement
   and any retained shared provider dependency.
3. Existing server-private provider credentials, Profile/account identifiers and
   history stay intact. A client-entry donor cannot simply be disabled/deleted:
   the existing Profile backend resolver requires its provider entry. Only an
   exact, already-authorized retained Profile/account binding can support a
   provider handoff; names, request payloads and today's default are insufficient.
4. Source continuity must keep original history/attribution unchanged and must
   never reactivate a retired device token or grant another Profile's authority.
   Ambiguous or partial ownership fails closed with explicit management feedback.
   No automatic OAuth, new login, account creation or shared token rotation.
5. Cleanup of one legacy client must not cascade to another client, shared
   Profile/account or history. HA2026.10 deletes the ConfigEntry before invoking
   `async_remove_entry` and catches callback errors: raising there cannot prevent
   deletion. The implementation must preserve dependencies before that boundary,
   not pretend that a callback exception is a deletion veto.
6. Migration/recovery must be idempotent, restart-safe and tested with partial
   failure. Real data and installation remain separately authorized effects.

## Before/after behavior scenarios

### Handoff transaction selected before migration implementation

Retain a Windows donor as a provider-only runtime. Transfer only when exactly
one healthy retained entry already refers to that donor and the current stored
Profile/backend/account/provider binding agrees. No destination is selected by
name, request identity or a new login. Zero or multiple eligible destinations
leave the donor quarantined with management feedback.

Serialize against the existing provider refresh lock. Validate all affected
entries first. Independent inspection of actual HA2026.10 disproved an initial
assumption: update listeners can start eagerly and ConfigEntry Store defaults
to non-atomic writes, swallowing write errors. Delayed-save acknowledgement is
therefore insufficient. Migration must use staged ownership, suppress our own
reload listeners during that transaction, and verify a fresh disk readback of
each completed state. Keep the original donor authoritative until a prepared
successor is saved and verified; keep donor credentials until activated
successor/references are saved and verified. Interrupted stages must resolve
from stored markers and exact current binding. No parallel Store writer or new
credential repository is introduced. If the existing HA save/readback boundary
cannot be verified, leave the provider quarantined and surface the failure.
HA2026.10 has no public ConfigEntries flush method. A bounded compatibility
adapter uses that manager's existing `_store.async_save`, never a second writer,
and verifies its actual on-disk file against the current public entry records.
Unavailable manager/Store fields fail closed. Provider resolution is fenced
through preparation/activation/rollback, including retained adapter views, so a
concurrent request cannot rotate the newly copied credentials during readback.
Acquire HA entry lifecycle locks before the existing provider refresh lock;
serialize the existing history-maintenance pass between those locks;
revalidate current entries, loaded runtimes and Profile/account/device ownership
after each awaited saved stage. Fence our reload and maintenance callbacks.
Finish the physical Store writer/readback even when cancelled, then roll back
only transfer-owned fields before releasing locks. Preserve concurrent Profile
or account management changes. Detect concurrent OAuth/provider-field updates
at every durable boundary, including rollback readback. Roll back only fields
still equal to this transfer's planned writes and replay skipped external update
listeners after releasing the fence; acknowledge only this transfer's affected
entries. A cold interrupted activated successor must still
pass the existing current Profile/account authority before provider use.
Handed-off live owners retain a dynamic backend view, so cached provider objects
also lose live authority after current Profile/default-account reassignment.
Historical continuation uses its captured account, independently of today's
default, and is withdrawn on actual source/account revocation. Existing unloaded
or disabled followers are repointed during cold recovery without loading them
or adding device authority. A newly arriving donor reference outside the held
lifecycle locks aborts and rolls back the transfer, preserving that reference
and the original donor connection.
Transfer provider keys only; destination device identity/token stays unchanged.
The donor loses provider keys after activation. Narrow server-owned history
continuity metadata binds the original donor ID to this exact successor and
Profile/account/backend/provider; historical row bodies remain unchanged.
Successor withdrawal, disablement, account changes and typed revocation invalidate
that continuity. Finish this transaction before a user removes the retired entry.
An arbitrary forced deletion of a quarantined unresolved provider is not claimed
preservation-safe; the Repair states that dependency explicitly.
Both retained-connection and removable Repairs name the existing configuration
and have distinct localized state titles; ignoring a native HA warning is not a
provider-transfer or deletion authorization.

- Actual HA wizard offers Windows today; all five locales must omit it after.
- Direct Windows selection/details/pairing and unknown explicit types must be
  rejected rather than becoming the default iOS client.
- A genuine old Windows token must not gain Apple authority by changing type,
  device prefix or nested identity; retained Apple/Pi/ESP routes still work.
- Legacy setup must safely quarantine transport without blocking other entries;
  repeated setup/restart and partial failure must preserve state.
- A Windows provider donor plus Apple peer on one exact Profile/account must
  retain backend, live auth, Ask DJ and history through retirement/removal.
- Removing only a Windows follower must retain the provider and other clients;
  ambiguous provider ownership must not guess, delete data or broaden authority.
- Profile reuse and duplicate-name recovery remain qualified; paired-live,
  conversation/history/search, expressive Moments and Cast1.1 regressions remain.

Capture baseline failures before producer edits using synthetic source-shaped
entries and the real HA flow/router/storage chain. Helper tests supplement that
proof. Small genuine wizard screenshots, migration/refusal receipts, independent
technical/privacy/UX review and immutable candidate/package readback are required.

## Reporting and effect boundary

Report `CORE_WINDOWS_CLIENT_REMOVAL`, `LEGACY_CONFIG_COMPATIBILITY`,
`RETAINED_CLIENT_REGRESSIONS`, `INSTALLED_ACCEPTANCE` and
`WINDOWS_INFRA_RETIREMENT` separately. The Core subset alone never completes the
parent retirement. Handoff exact source/receipts and remaining dependencies to
Windows #76. No Windows-repo, runner/service/workflow/protection/secret, VM/.NET,
website, native Apple, receiver, Pages or app-release changes. Source and separate
Finalization retain distinct exact publication gates. Stop after this one slice.
