# DJConnect Repository Ownership

This document clarifies repository boundaries. The HA/HACS repository remains the canonical foundation source of truth for platform direction.

## `pcvantol/djconnect`

Owns: Home Assistant integration, local-first backend runtime, canonical foundation docs, canonical language contract, DJConnect Profile orchestration, canonical Profile Resolver, Request Context / ProfileResolutionContext model, Voice Endpoint/HA device/area/profile mappings, Assist-to-Profile orchestration, Music Backend orchestration, Track Insight orchestration, Ask DJ, Music DNA, OTA/status/diagnostics and HA-facing API contracts.

Does not own: native client UX code, ESP32 firmware implementation, public website implementation, central APNs provider credentials or release artifact repositories.

Must follow: the full platform foundation and Home Assistant/HACS quality expectations.

Update canonical docs when: product direction, architecture principles, domain language, repository boundaries, API contracts, ADRs or cross-repo release rules change.

Request-source ownership examples:

- Apple and Windows clients send the profile/device context they can reliably
  know.
- ESP32 sends its registered DJConnect device identity.
- Raspberry Pi sends device/profile context as appropriate for an Ambient
  Client.
- The HA integration derives Voice Endpoint, Home Assistant device/entity,
  area/room and Assist pipeline context from Home Assistant.
- Clients must not invent durable personal identity when the backend cannot
  resolve one.

## `pcvantol/djconnect-app`

Owns: Apple Intelligence Client UX for iOS, macOS and watchOS.

Also owns: correct localized rendering for Apple presentation and distribution
surfaces.

Does not own: backend intelligence, Music DNA storage, Spotify OAuth secrets, central relay logic, canonical Profile resolution or canonical foundation docs.

Must follow: DJConnect Profile, Device, Music Backend, Renderer/Client, privacy and push/bootstrap contracts from the canonical foundation.

Update canonical docs when: Apple UX requires new shared client capabilities, API contracts, profile rules or product language.

## `pcvantol/djconnect-windows`

Owns: Windows Intelligence Client UX.

Also owns: correct localized rendering for Windows presentation and
distribution surfaces.

Does not own: backend intelligence, provider-specific playback logic, canonical Ask DJ history, canonical Profile resolution or foundation docs.

Must follow: shared client contracts, Music Backend capability behavior, DJConnect Profile boundaries and privacy rules.

Update canonical docs when: Windows introduces reusable client capability requirements or shared platform language.

## `pcvantol/djconnect-pi`

Owns: Raspberry Pi Ambient Client.

Also owns: correct localized rendering for Pi presentation and distribution
surfaces.

Does not own: canonical backend intelligence, Music DNA storage, Spotify credentials, canonical Profile resolution or foundation docs.

Must follow: Device/runtime boundaries, renderer/client responsibilities, local-first pairing and backend-owned intelligence contracts.

Update canonical docs when: Pi capabilities change shared Ambient Client expectations or runtime contracts.

## `pcvantol/djconnect-esp32`

Owns: ESP32 Voice/Control Client firmware.

Also owns: correct localized rendering for firmware, constrained device UI and
web portal surfaces.

Does not own: Spotify credentials, backend playback orchestration, Music DNA, Ask DJ chat history, canonical Profile resolution or foundation docs.

Must follow: Device identity, firmware protocol, local device API, pairing, OTA, privacy and backend command contracts.

Update canonical docs when: firmware changes require new platform protocol, Device model or release governance decisions.

## `pcvantol/djconnect-api`

Owns: central API trust/relay boundary, APNs relay, per-install token bootstrap and future entitlement/profile-cloud surfaces.

Also owns: localized display-message mapping for API-owned user-facing errors
where the API, rather than a client, owns the display copy.

Does not own: local-first Community runtime, Home Assistant integration behavior, client UX or canonical foundation docs.

Must follow: local-first value, optional cloud extension, privacy, profile boundary and central trust rules.

Update canonical docs when: central API responsibilities expand into entitlement, cloud profile, sync, trust or privacy policy changes.

## `pcvantol/djconnect-website`

Owns: public product story, onboarding, documentation presentation and release/download guidance.

Also owns: correct localized rendering for public website, metadata,
onboarding and support surfaces.

Does not own: runtime contracts, canonical architecture decisions, client implementation or release artifacts.

Must follow: product language, tier language, Spotify non-affiliation wording, privacy claims and canonical roadmap positioning.

Update canonical docs when: website work reveals product-language drift, onboarding contract gaps or public positioning changes.

## `pcvantol/djconnect-firmware`

Owns: public firmware release distribution artifacts only.

Also owns: localization consistency for end-user release/install copy stored in
the repository or attached to releases.

Does not own: ESP32 source code, firmware architecture, HA integration behavior or foundation docs.

Must follow: release artifact naming, manifest, licensing, security and release governance rules.

Update canonical docs when: firmware distribution format or release governance needs a platform-level change.

## `pcvantol/djconnect-app-releases`

Owns: public app release artifacts only.

Also owns: localization consistency for end-user release/install copy stored in
the repository or attached to releases.

Does not own: Apple client source, backend contracts, entitlement model or foundation docs.

Must follow: release governance, product language, privacy and distribution rules.

Update canonical docs when: app release distribution strategy changes platform release governance or public product promises.

## `pcvantol/djconnect-pi-releases`

Owns: public Raspberry Pi release artifacts only.

Also owns: localization consistency for end-user release/install copy stored in
the repository or attached to releases.

Does not own: Pi source code, backend contracts, canonical docs or client architecture.

Must follow: release governance, artifact integrity, licensing and privacy rules.

Update canonical docs when: Pi release packaging or distribution changes cross-repo release strategy.
