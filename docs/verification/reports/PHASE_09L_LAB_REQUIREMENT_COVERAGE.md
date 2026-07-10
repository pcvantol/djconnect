# Phase 09L Lab Requirement Coverage

Status: generated from canonical scenario catalog

## Summary

- Total scenarios: 231
- Classified scenarios: 231
- Unresolved scenarios: 0

## Scenarios Per Lab Profile

- `ha-assist`: 17
- `ha-full`: 1
- `ha-minimal`: 33
- `ha-music`: 88
- `ha-profile`: 92

## External Or Physical Requirements

- `apple.runtime`: 94
- `esp32.runtime`: 10
- `github.ci`: 18
- `music.spotify_direct`: 18
- `network.internet`: 39
- `pi.runtime`: 26
- `release.artifacts`: 18
- `voice_endpoint.runtime`: 16
- `website.runtime`: 10
- `windows.runtime`: 86
- hardware `esp32`: 10
- hardware `raspberry_pi`: 26
- hardware `voice_endpoint`: 16

## Top Capabilities

- `evidence.storage`: 231
- `djconnect.capabilities`: 223
- `djconnect.loaded`: 223
- `ha.access_token`: 223
- `ha.logs`: 223
- `ha.rest`: 223
- `ha.runtime`: 223
- `ha.services`: 223
- `ha.websocket`: 223
- `ha.storage`: 145
- `djconnect.profile_platform`: 136
- `ha.persistence`: 98
- `apple.runtime`: 94
- `windows.runtime`: 86
- `music.fake_backend`: 47
- `djconnect.ask_dj`: 44
- `djconnect.pairing`: 35
- `djconnect.music_dna`: 34
- `music.playback_target`: 31
- `djconnect.profile_resolution`: 28
- `ha.registries`: 28
- `pi.runtime`: 26
- `djconnect.playback`: 23
- `djconnect.private_session`: 20
- `music.spotify_direct`: 18
- `github.ci`: 18
- `release.artifacts`: 18
- `voice_endpoint.runtime`: 16
- `djconnect.export_import`: 12
- `ha.restart`: 10

## Profiles

### ha-assist
- Services: `homeassistant`, `piper`, `whisper`
- Compose fragments: `docker/verification/compose.base.yaml`, `docker/verification/compose.whisper.yaml`, `docker/verification/compose.piper.yaml`
- Capabilities: 28

### ha-full
- Services: `evidence_helper`, `fake_music_backend`, `homeassistant`, `music_assistant`, `piper`, `whisper`
- Compose fragments: `docker/verification/compose.base.yaml`, `docker/verification/compose.whisper.yaml`, `docker/verification/compose.piper.yaml`, `docker/verification/compose.fake-backend.yaml`, `docker/verification/compose.music-assistant.yaml`, `docker/verification/compose.observability.yaml`
- Capabilities: 36

### ha-minimal
- Services: `homeassistant`
- Compose fragments: `docker/verification/compose.base.yaml`
- Capabilities: 12

### ha-music
- Services: `fake_music_backend`, `homeassistant`, `music_assistant`
- Compose fragments: `docker/verification/compose.base.yaml`, `docker/verification/compose.fake-backend.yaml`, `docker/verification/compose.music-assistant.yaml`
- Capabilities: 27

### ha-profile
- Services: `homeassistant`
- Compose fragments: `docker/verification/compose.base.yaml`
- Capabilities: 20

## Unresolved Scenarios

None.
