# Voice Endpoint Adoption Report

## Implemented

- Voice Endpoints are modeled as Request Context signals, not identities.
- `ProfileResolutionContext` now accepts `voice_endpoint_id`,
  `assist_pipeline_id`, `satellite_id`, `ha_device_id`, `area_id`, `room_id`,
  `player_id`, `playback_zone_id` and `request_source`.
- The single canonical `ProfileResolver` resolves in this order:
  explicit profile, DJConnect device mapping, Voice Endpoint / HA device
  mapping, HA user hint, area or room mapping, player or playback-zone mapping,
  fallback profile, then `ProfileRequired`.
- Household storage supports explicit mappings for Voice Endpoints, HA devices,
  HA users, areas, rooms, players and playback zones.
- Home Assistant Assist conversation requests are converted into request
  context where Home Assistant exposes useful signals.
- `run_text_command` can apply Profile Platform request context before Ask DJ
  and playback execution, so backend routing and private-session policy use the
  resolved Profile.
- WebSocket `djconnect/capabilities` advertises Voice Endpoint-aware request
  context and mappings through the existing capability surface.
- HTTP voice header parsing accepts `X-DJConnect-Voice-Endpoint-ID` and
  `X-DJConnect-Assist-Pipeline-ID` in addition to legacy satellite/area/player
  headers.

## Deferred

- A Home Assistant config/options UI for editing Voice Endpoint and area
  mappings.
- Automatic exhaustive extraction for every future Home Assistant Assist
  internal field shape.
- Speaker recognition.
- Voiceprints.
- Cloud Profiles.
- Cloud voice endpoints.

## Current Limitations

- Voice Endpoint mappings must currently be written through Profile Platform
  storage/helpers or future services/UI, not a polished end-user flow.
- Home Assistant conversation metadata differs by HA version and voice
  implementation; DJConnect only copies fields that are actually present.
- HA user IDs remain hints and do not imply personal identity for shared voice
  interactions.

## Future Speaker Recognition

Speaker recognition may become an additional resolver hint later. It must not
override explicit profile, device, Voice Endpoint or area mappings, and it must
not create a second resolver.

## Future Voiceprint Support

Voiceprints are out of scope for this phase. Any future voiceprint data must be
opt-in, profile-scoped, privacy-reviewed and kept out of diagnostics/logs.

## Future Cloud Voice Endpoints

Cloud Assist entrypoints can use the same Request Context model by providing
stable request-source signals to the canonical resolver. They should not become
Profiles, DJConnect Devices or Users by default.

Voice Endpoints are Request Sources. They are not identities.
