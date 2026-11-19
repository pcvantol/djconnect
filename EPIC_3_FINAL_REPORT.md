# Epic 3 Final Report

Status: complete  
Date: 2026-07-10  
Final decision: GO

## Executive Summary

Epic 3 and Epic 3B are accepted. DJConnect now has an accepted Profile Platform
baseline: Profile is the durable identity, Request Context is canonical, one
Profile Resolver owns resolution, client classes share a common contract, and
privacy rules are strong enough for the Intelligence Platform to start.

No critical architectural defect was found that requires additional Epic 3
implementation. Remaining issues are backlog, not closure blockers.

## Architecture Delivered

- DJConnect Profile is the primary identity for personal and shared state.
- Request Context / `ProfileResolutionContext` is the canonical interaction
  input.
- One `ProfileResolver` resolves explicit profile, device, Voice Endpoint, HA
  user, area/room, playback zone and fallback signals.
- Music Backend and Music Account remain backend/provider boundaries.
- Devices and clients remain runtime/rendering surfaces, not identity owners.
- Repository ownership remains aligned with `REPOSITORY_OWNERSHIP.md`.

## Backend Delivered

- Profile storage, profile mappings, backend/account metadata and resolver
  support exist in the Home Assistant integration.
- Services, REST handlers and websocket paths route profile-aware behavior
  through shared backend handlers where personal/backend state applies.
- Capability discovery advertises profile and request-context support.
- Contract fixtures define request, response, error, capability and privacy
  behavior.
- Voice Endpoint, HA device, area and playback zone signals route through the
  same resolver model.

## Client Adoption Summary

| Client | Role | Adoption | Status |
| --- | --- | --- | --- |
| Apple | Intelligence Client | Complete | Reference |
| Windows | Intelligence Client | Complete | Parity |
| Pi | Ambient Client | Partial | Shared-first |
| ESP32 | Voice & Control Client | Complete | Reference |
| Voice Endpoint | Voice Endpoint | Partial | Shared-first |

## Profile Platform Summary

The platform now treats Profile as the only durable identity. Devices, HA users,
rooms, Voice Endpoints and playback zones are resolver signals. Personal state
must attach to Profile, not client/device/runtime identity.

## Platform Baseline

The accepted platform baseline is captured in `PLATFORM_BASELINE_v1.md`.

## Resolver Summary

Only one resolver exists. The accepted deterministic order is explicit profile,
device mapping, Voice Endpoint/HA device mapping, HA user hint, area/room
mapping, playback player/zone mapping, fallback and structured error.

Request Context is the canonical input to the Profile Resolver.

Devices, Voice Endpoints, HA users, Areas and Playback Zones are resolution
signals. They are not identities.

No client-side, Voice-specific or Device-specific resolver is accepted.

## Privacy Summary

Privacy review passes.

- Request Context excludes tokens, provider credentials, raw prompts, raw
  audio, Ask DJ history and Music DNA contents.
- Private Session suppresses personal persistence.
- Shared, guest, room and household contexts remain safe by default.
- Voice Endpoints do not automatically expose personal history or Music DNA.
- Diagnostics/export behavior is required to redact secrets and personal
  history.

## Capability Summary

The canonical capability baseline is `profile_context: 1` and
`client_contract_fixtures: 1`, discovered through `djconnect/capabilities`.

Profile Platform, Request Context, capability discovery, contract versioning,
structured profile errors and privacy expectations are accepted as platform
contracts for Epic 4.

## Architecture Fitness

| Platform principle | Result | Notes |
| --- | --- | --- |
| Everything personal belongs to a DJConnect Profile | PASS | Profile owns personal state and intelligence memory. |
| Every interaction resolves a Profile from Request Context | PASS | Profile-aware surfaces use `ProfileResolutionContext`. |
| Everything hardware/client/runtime-specific belongs to a Device | PASS | Device state remains runtime/capability/status state. |
| Everything playback/provider-specific belongs behind a Music Backend | PASS | Provider behavior remains adapter-owned. |
| Everything durable intelligence-related belongs to the backend | PASS | Clients are contract consumers and renderers. |
| Everything presentation-specific belongs to a Renderer/Client | PASS | UI remains client-owned. |
| Everything temporary belongs to a Session with expiry | PASS | Follow-up/session/private behavior remains temporary by contract. |
| Everything experimental belongs behind a Feature Flag | WARNING | Feature maturity exists in foundation docs; platform-wide runtime flags are Epic 5 work. |
| Everything shared must be privacy-aware by default | PASS | Shared and Voice Endpoint contexts default safely. |
| Everything cross-repo starts from the canonical foundation | PASS | This repo remains canonical source of truth. |

## Contract Validation

Accepted:

- canonical request contract;
- canonical response target;
- canonical error categories/wire codes;
- capability discovery;
- profile fixture consistency;
- shared client-class requirements.

No client-specific identity contract is accepted. Client-specific rendering is
allowed only behind the shared backend contract.

## Known Technical Debt

Must fix before Epic 4:

- None identified.

Should fix during Epic 4:

- keep profile context attached to all new Insight Feed entrypoints;
- preserve fixture coverage as intelligence contracts expand;
- avoid reintroducing feature-local identity in Track Insight, Discover or
  recommendations.

Future:

- richer `resolved_profile` metadata where privacy-safe;
- polished HA mapping UI for Voice Endpoints, areas and playback zones;
- cross-repository fixture dashboard;
- profile-native Ask DJ history migration if legacy HA-user keyed storage
  remains in older paths.

Never:

- client-side Profile Resolver;
- client-owned Music DNA;
- device-owned durable personal identity;
- Voice-specific resolver fork.

## Known Product Debt

- Terminology needs continued public cleanup in website/release surfaces.
- Community, Personal, shared and household UX need product-story refinement.
- Pi Ambient Client needs a formal capability budget.
- Voice Endpoint UX needs admin-friendly mapping and validation.
- Consumer onboarding remains broader platform work outside Epic 3.

## Lessons Learned

- Profile identity had to be solved before larger intelligence work.
- Voice Endpoints are request sources, not automatically DJConnect Devices.
- Fixture contracts are the right guardrail for multi-client parity.
- Privacy rules must be part of identity resolution, not a later UI concern.
- Home Assistant remains the primary runtime of DJConnect. It is not the
  architectural boundary of the platform. Reference:
  `docs/research/R0_RUNTIME_INDEPENDENCE.md`.

## Recommendations

- Start Epic 4 with `PLATFORM_BASELINE_v1.md` as the non-negotiable identity
  baseline.
- Define Insight Feed as backend-owned and profile-scoped from day one.
- Keep client adoption validated through fixture contracts.
- Move feature maturity and strict parity governance into Epic 5.
- Keep distribution, website and public-language cleanup in Epic 6/Epic 8.
- No future Intelligence feature should introduce new identity ownership
  outside the Profile Platform.
- Every new capability should first be placed inside the Domain Model before
  implementation.

## Epic 4 Readiness

GO.

DJConnect is ready to build the Intelligence Platform. Start Epic 4:
Intelligence Platform.
