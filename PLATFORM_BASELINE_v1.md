# DJConnect Platform Baseline v1

Status: Accepted
Date: 2026-07-10  
Version: Profile Platform v1
Baseline owner: `pcvantol/djconnect`

## Purpose

This document captures the officially accepted DJConnect platform baseline
after Epic 3 and Epic 3B.

The foundation describes platform principles. This baseline describes the
accepted implementation architecture those principles produced for the Profile
Platform.

Future platform work starts from this baseline.

## Version Baseline

Profile Platform Version: 1  
Resolver Version: 1  
Request Context Version: 1  
Profile Contract Version: 1  
Capability Contract Version: 1  
Privacy Contract Version: 1

| Contract | Accepted version | Source of truth |
| --- | ---: | --- |
| Profile Platform | 1 | `DOMAIN_MODEL.md`, `ARCHITECTURE_PRINCIPLES.md`, ADR-0001 |
| Profile Resolver | 1 | `custom_components/djconnect/domain/resolver/profile_resolver.py` |
| Request Context | 1 | `ProfileResolutionContext`, ADR-0011 |
| Profile Adoption Contract | 1 | `docs/implementation/epic3b/01-profile-adoption-contract.md` |
| Capability Discovery | 1 | `examples/client_contracts/capabilities.websocket.json` |
| Privacy Contract | 1 | Profile privacy/export implementation and fixtures |

## Canonical Components

The accepted Profile Platform v1 baseline includes these canonical components:

- Profile
- Request Context
- Profile Resolver
- Music Backend abstraction
- Music Account abstraction
- Playback Zone abstraction
- Capability Discovery
- Profile Adoption Contract v1
- Privacy Contract v1

## Accepted Identity Model

DJConnect Profile is the only durable identity for personal and shared
DJConnect state.

Profiles own:

- Music DNA;
- Ask DJ history and profile-scoped intelligence state;
- preferences, mood, privacy mode and recommendation signals;
- preferred music backend, music account and fallback playback zone.

Devices, clients, Home Assistant users, Voice Endpoints, rooms, areas, players
and playback zones are request-context signals or runtime objects. They do not
own durable personal state.

## Accepted Request Context Model

Every profile-aware interaction enters the platform through Request Context.
The current runtime type is `ProfileResolutionContext`.

Accepted request sources:

- Apple clients;
- Windows clients;
- Raspberry Pi clients;
- ESP32 clients;
- Home Assistant Voice Endpoint / Assist requests;
- Home Assistant services, websocket calls and REST/API handlers.

Future request sources must add signals to Request Context and route through
the canonical Profile Resolver. They must not create a new identity model.

## Accepted Resolver Constraints

There is one canonical Profile Resolver.

Resolution order:

1. explicit profile selection;
2. DJConnect device mapping;
3. explicit Voice Endpoint / satellite / HA device mapping;
4. Home Assistant user hint;
5. area or room mapping;
6. playback player or playback zone mapping;
7. configured fallback profile;
8. structured profile error.

Deterministic rules:

- invalid explicit profile selection fails instead of falling through;
- explicit profile selection wins over all inferred signals;
- device mapping wins over room/area inference;
- explicit Voice Endpoint mapping wins over inferred area mapping;
- shared Voice Endpoints default to shared, room, household, guest-safe or kids
  profiles unless explicitly configured otherwise;
- future speaker identity may be a hint only and must use the same resolver.

## Accepted Client Classes

Profile Platform v1 accepts these client classes:

- Intelligence Client
- Ambient Client
- Voice & Control Client
- Voice Endpoint
- Presentation Client

| Client class | Current examples | Baseline role |
| --- | --- | --- |
| Intelligence Client | Apple, Windows | Rich personal UI; sends device/profile context; renders backend-owned state. |
| Ambient Client | Raspberry Pi | Shared room/household display and control; defaults safely to shared context. |
| Voice & Control Client | ESP32 | Physical control surface; no durable personal intelligence ownership. |
| Voice Endpoint | HA Voice Endpoint | Spoken request source and mapping signal; no automatic personal identity. |
| Presentation Client | VibeCast / future TV renderer | Shared rendering of backend-owned intelligence output. |

## Accepted Capability Baseline

Clients discover profile support through `djconnect/capabilities`.

Accepted profile capabilities:

- `profiles`;
- `explicit_profile_selection`;
- `private_sessions`;
- `profile_export`;
- `request_context`;
- `voice_endpoint_request_context`;
- `voice_endpoint_mappings`.

Accepted contract versions:

- `profile_context: 1`;
- `client_contract_fixtures: 1`.

## Accepted Privacy Baseline

The Profile Platform privacy baseline is accepted with these constraints:

- OAuth tokens, refresh tokens, Home Assistant tokens, APNs tokens, device
  tokens, raw prompts, raw audio, Ask DJ history and Music DNA contents are not
  request-context fields.
- Diagnostics and exports must redact or exclude secret and personal-history
  data.
- Private Session suppresses personal persistence where a feature would
  otherwise write profile state.
- Shared, guest, room and household profiles do not automatically expose
  personal Ask DJ history or Music DNA.
- Voice Endpoints do not infer personal identity from room or ambiguous speaker
  context.

## Platform Parity Matrix

Legend: Supported, Future, Not Applicable.

| Capability | Apple | Windows | Pi | ESP32 | Voice Endpoint |
| --- | --- | --- | --- | --- | --- |
| Profile Platform | Supported | Supported | Supported | Supported | Supported |
| Profile Switching | Supported | Supported | Future | Not Applicable | Future |
| Shared Profiles | Supported | Supported | Supported | Supported | Supported |
| Private Session | Supported | Supported | Future | Not Applicable | Supported |
| Music DNA | Supported | Supported | Future | Not Applicable | Not Applicable |
| Ask DJ | Supported | Supported | Supported | Voice/PTT only | Supported |
| Recommendations | Supported | Supported | Future | Not Applicable | Future |
| Track Insight | Supported | Supported | Supported | Not Applicable | Future |
| Capability Discovery | Supported | Supported | Supported | Supported | Supported |
| Profile Cache | Supported | Supported | Future | Not Applicable | Not Applicable |
| Error Handling | Supported | Supported | Supported | Supported | Supported |
| Contract Version | Supported | Supported | Supported | Supported | Supported |
| Playback Routing | Supported | Supported | Supported | Supported | Supported |
| Privacy | Supported | Supported | Supported | Supported | Supported |

## Accepted Architectural Constraints

- Profile is the only durable identity for personal and shared state.
- Request Context is the only input to the Profile Resolver.
- One canonical Profile Resolver owns identity resolution.
- Devices, Voice Endpoints, Home Assistant users, Areas and Playback Zones are
  resolver signals, not identities.
- Music Backend and Music Account abstractions own provider-specific behavior.
- Playback Zone owns playback target context without becoming identity.
- Backend owns intelligence, personal state and durable memory.
- Clients render backend-owned state and may not own personal intelligence.
- Devices never own personal state.
- Voice Endpoints are request sources and mapping signals, not automatic
  personal identities.
- Capability Discovery advertises supported platform contracts before clients
  depend on them.
- Profile Adoption Contract v1 is the shared client adoption contract.
- Privacy Contract v1 applies to every profile-aware request, including shared,
  guest, room, household, Voice Endpoint and private-session contexts.
- Repository ownership remains as defined in `REPOSITORY_OWNERSHIP.md`.

## Baseline Debt Carried Forward

These items do not block Epic 3 acceptance:

- richer `resolved_profile` response metadata is not universal;
- polished Home Assistant mapping UI for Voice Endpoints/areas/zones remains
  follow-up UX work;
- sibling repositories still need ongoing fixture conformance visibility;
- formal required/optional/forbidden client parity belongs in Epic 5;
- distribution and public product-language cleanup belongs in Epic 6/Epic 8.

## Governance

This baseline is not a new epic and does not reopen Epic 3. It records the
accepted platform state after Epic 3 acceptance review.

Future identity, intelligence, recommendation, insight, voice, client and
runtime work must start from Profile Platform v1 unless a later accepted ADR or
platform baseline explicitly supersedes it.
