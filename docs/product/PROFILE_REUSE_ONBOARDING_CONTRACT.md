# Explicit Profile reuse during onboarding

Assignment `DJC-CORE-PROFILE-REUSE-ONBOARDING-V1-20261008` builds on protected
base `3488fd82ed04804973039b909f61a34e76379659`. The existing Household,
Profile, Device, Music Account and provider adapters remain authoritative.

## User-visible flow

After selecting/pairing the client, profile choice precedes provider/account
setup. An existing household offers its actual current profile names plus
Create a new profile. An empty household goes directly to new-profile details.
The new-profile form also offers existing profiles so a duplicate-name error
can be recovered without abandoning pairing. Existing profile IDs are selected
explicitly; a matching name never authorizes reuse. Disabled profiles cannot
be reused. Choices are sorted by normalized name then exact ID.

New-profile details, provider selection and OAuth results remain flow-local
until the final confirmation. New-profile uniqueness uses the existing strip
and casefold rules; a duplicate produces a localized name-field error. At
confirmation a selected profile is re-read and compared with its captured
state. A changed/deleted selection refreshes the real choices and requires
explicit selection again. Concurrent onboarding commits serialize. The existing
storage writer serializes all writes; a staged onboarding update becomes visible only after persistence.
Cancellation finishes any pending file write and restores current committed
state. Concurrent Profile edits are retained; conflicting onboarding returns
a retry form instead of overwriting them. Cancellation does not leave
new Profiles, accounts, backend registrations or device mappings.

Reuse only adds the new Device mapping and config-entry profile/account IDs.
It preserves the profile, preferences, accounts, backend registration, existing
devices and Household fallback. Creating another new profile also preserves
an established fallback/backend registration; only first-profile setup sets
initial fallback policy. Assist entries retain the same profile binding.

## Existing provider connection

Domain models deliberately contain no OAuth credentials. The new config entry
references its existing HA-owned provider entry with `profile_backend_entry_id`;
it does not copy refresh tokens, client IDs or Music Assistant player settings.
Selection requires one unambiguous configured provider owner for the exact
Profile/current account/backend. Missing or disabled/ambiguous connections give
a localized profile-field error rather than a forced new OAuth flow. Legacy
Assist entries lacking an explicit account ID qualify only through the original
canonical single-active-account chain and matching stored provider client ID.

The existing runtime configuration and provider adapters resolve that reference
against current HA entries and Household device/profile/account mappings.
Only provider configuration is inherited internally. New-device identity and
authentication remain local; no credential enters forms or client responses.
A stateless adapter view retains caller identity, profile/privacy context and
playback/device state while sharing only the original provider's token cache,
refresh lock and rotation persistence. It introduces no second Runtime. Music
Assistant retains the original connection/player.
Every retained view revalidates current authority before provider config/cache/
rotation access. Cross-profile overrides, remapping, source removal/unload,
replacement and disabled accounts fail closed without silently rebinding. There is no
fallback to another profile's connection or copied stale token.
This is bounded adapter reuse, with no new endpoint, command engine, provider,
Profile architecture or durable knowledge migration.

## Localization and evidence boundary

`strings.json` and en/nl/de/fr/es provide both profile forms, selectors and
specific duplicate/missing/changed/connection/save errors. Existing HA form
rendering owns presentation. No Swift source changes.

Five initially failing real config-flow regressions bind missing early choice,
duplicate-name generic failure, premature persistence, missing preserved reuse
and removed selection. Expanded tests cover draft cancellation, concurrent
creation, fallback/backend/account preservation, source-owner ambiguity,
provider refresh/current reference, disabled profiles and save failure.

Real HA config-flow and existing HA frontend qualification use a disposable
local HA instance, the already installed HA image, synthetic accounts/devices
and declared Assist/provider fixtures. No live Spotify/MA playback, audio,
HA-dev install, or installed native-client acceptance is inferred from it.
Before/after screenshots and flow/state sequences remain separate from tests.

Read-only recent HA-dev logging found ordinary custom-component warnings, one
Spotify HTTP500 and one missing-bearer rejection. These do not justify broader
retry, authentication or logging changes. Only reproduced onboarding/validation
problems are changed. Two additional before-failing repair cases prove that a
manual ESP must not request Spotify OAuth, and a shared ESP must not create its
own OAuth prerequisite issues or clear the original owner’s global issues.
Shared-client options retain reauthorization at the original connection. Each
protected source/Finalization publication and any HA-dev installation requires its own explicit candidate-specific authorization.


## Acceptance sequence and regression ownership

The before scenarios were run against the exact base above before implementation:
missing early profile selection, a duplicate reported only as a generic failure,
a prematurely committed new Profile, absent preserved reuse, and a removed
selection without a fresh choice. Their five failures are independent of the
additional manual/shared ESP OAuth Repair regressions, which also fail at base.

The after browser sequence uses actual HA config-flow HTTP responses and the
existing frontend, with a synthetic app paired through the existing pair route:

1. Empty Household: pairing → new-profile details → backend → confirmation →
   entry. Exactly one Profile and one Device mapping are persisted.
2. Second device: pairing → profile dropdown → explicitly select Home →
   confirmation → entry. No backend or OAuth form; exactly one Profile and two
   Device mappings. Profiles, accounts, backends and fallback compare equal.
3. Third device: choose new → enter ` HOME ` → localized name-field error.
   Household remains byte-equivalent as structured data. Explicitly choose Home
   on that same form → confirmation → entry; one Profile, three mappings.

Before screenshots show the old backend-before-profile form and generic error.
After screenshots show the real choice list, first creation, reuse, name error
and recovery. A separate frontend locale matrix verifies actual HA locale and
renders both forms in en/nl/de/fr/es. These are software/browser qualifications;
they do not establish live provider, native-client, installed HA-dev or Pi proof.

`tests/test_profile_onboarding.py` owns the onboarding and provider-reference
regressions, `tests/test_config_flow_helpers.py` retains existing flow/provider/
Assist compatibility, and `tests/test_repairs.py` owns the two bounded Repair
regressions. Event-controlled storage tests prove cancellation and concurrent
edit behavior without timing sleeps. The existing whole-suite and Golden
qualification remain intact. This implementation does not redefine the
platform verification planner or Golden scenario families.

Reproducible evidence accompanies the completion receipt under
`artifacts/verification/profile-reuse-onboarding`: corrected base failures,
whole-suite/coverage/lint, independent review, before/after screenshots,
`browser-exact-flow-sequence.json`, `browser-exact-preservation.json` and
`five-language-browser-readback.json`. Synthetic HA authorization stays outside
that evidence; complete HA auth/config-entry stores must never be uploaded.

## Protected completion receipt

PR [#1130](https://github.com/pcvantol/djconnect/pull/1130) protected merged as
`3bb6bb8a9cb3e87ebb1bb51c0cf99dfbe572c283` from exact reviewed candidate
`162104d625f26a281cb20897ea5365c10bbdabff`, tree
`8a9dd2353eaf30edbba1b24a32d191691dc689d0`. The owner explicitly approved
this source merge and distinct automatic internal SHA-prerelease.

Exact source/main suites: 1,628 tests, seven existing skips, PASS; Ruff,
coverage, Golden Smoke and required source/main checks PASS. Independent exact
technical and UX review GO,249 independently executed tests,20 inspected real
HA screenshots. The exact internal archive contains130 safe byte-equal files;
SHA256 `d2ab2cd702d71e2f92b7ab4c03831aca2098e5034a6e7dc7853b56a7f18dff66`.
Canonical qualification JSON SHA256
`242d0d483d67fe1d81a5a221609a3f3f79420fba45743107528b1e7b64731c9c`:
integrity and every required check PASS. Coverage artifact digest
`4a002cdd29b9c48c0a8accb6de3883667f02162bb8ad9008e4feaa1bc47dd658`.
Automatic package and evidence workflows passed first attempt; no extra manual
Validate run, retry or evidence replacement was needed.

The [immutable completion history](../history/prompts/2026-10-08-profile-reuse-onboarding-finalization.md)
records before/after, three corrected independent-review findings, five-language
frontend results and boundaries. Separate eight-document Finalization requires
its own exact review/checks/publication authorization; its final receipt and
cleanup remain external. No installation, native or live-provider acceptance is
implied by this software/browser delivery.
