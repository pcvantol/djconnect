# DJConnect Scenario Catalog
Status: Canonical Scenario Catalog v1  
Scope owner: `pcvantol/djconnect`  
Applies to: DJConnect platform-wide verification  
Builds on: `docs/verification/00_VERIFICATION_VISION.md`, `docs/verification/01_VERIFICATION_ARCHITECTURE.md`, `verification/schema/scenario.schema.yaml`
## Purpose
This catalog defines durable DJConnect platform behavior as executable scenarios. It is not the verification harness, not adapter implementation and not a test runner. Each scenario describes expected behavior that Phase 4 and later verification adapters can execute through Home Assistant, clients, firmware, release artifacts or manual evidence collection.
The catalog intentionally favors breadth. The goal is to stop rediscovering what should be tested and instead choose which existing scenarios can be automated, executed manually or deferred with a documented limitation.
## Catalog Rules
- Scenario IDs are stable long-term references.
- Scenario YAML files are the canonical assets; this document is the human index.
- Scenarios describe platform behavior and evidence requirements, not implementation details.
- Scenarios declare logical runtime requirements in `requires`.
- Adapters may map one scenario to many concrete runtimes, but may not change expected results.
- Evidence must remain privacy preserving and follow the redaction rules in the schema and scenario files.
## Location
Scenario files live under `verification/scenarios/`, grouped by category.

## Runtime Requirement Classification

All canonical scenario files include a validated `requires` declaration.
Requirements are expressed as logical capabilities, services, integrations,
bootstrap state, resources, hardware and named secrets. They intentionally do
not include Docker Compose filenames, image tags, host paths or container
names.

The capability taxonomy lives in:

```text
verification/lab/capabilities.yaml
```

The current coverage report is generated at:

```text
docs/verification/reports/PHASE_09L_LAB_REQUIREMENT_COVERAGE.md
docs/verification/reports/PHASE_09L_LAB_REQUIREMENT_COVERAGE.json
```

The Planning Engine aggregates these requirements across the selected scenario
set and chooses the smallest canonical lab profile that satisfies the local lab
requirements. Future client, hardware and external capabilities remain explicit
resource requirements and are not silently mapped to a larger HA lab profile.
## Summary
| Group | Scenario files | Directory |
| --- | ---: | --- |
| SETUP | 25 | `verification/scenarios/setup/` |
| PROFILE | 24 | `verification/scenarios/profile/` |
| RESOLVER | 20 | `verification/scenarios/resolver/` |
| ASK_DJ | 28 | `verification/scenarios/ask_dj/` |
| MUSIC_DNA | 18 | `verification/scenarios/music_dna/` |
| DISCOVER | 16 | `verification/scenarios/discover/` |
| TRACK_INSIGHT | 8 | `verification/scenarios/track_insight/` |
| PLAYBACK | 10 | `verification/scenarios/playback/` |
| BACKEND | 8 | `verification/scenarios/backend/` |
| PRIVACY | 10 | `verification/scenarios/privacy/` |
| LOCALIZATION | 10 | `verification/scenarios/localization/` |
| CAPABILITIES | 8 | `verification/scenarios/capabilities/` |
| VOICE | 8 | `verification/scenarios/voice/` |
| HARDWARE | 10 | `verification/scenarios/hardware/` |
| NETWORKING | 8 | `verification/scenarios/networking/` |
| RELEASE | 8 | `verification/scenarios/release/` |
| EXPORT | 6 | `verification/scenarios/export/` |
| IMPORT | 6 | `verification/scenarios/import/` |
| Total | 231 | `verification/scenarios/` |

## Scenario Groups

### SETUP
- `SETUP-001` Fresh installation creates baseline platform state
- `SETUP-002` Fresh installation exposes capability discovery
- `SETUP-003` Fresh installation preserves Spotify non-affiliation notice
- `SETUP-004` Upgrade migrates profile platform state
- `SETUP-005` Upgrade preserves Ask DJ history revisions
- `SETUP-006` Upgrade preserves Music DNA opt-in setting
- `SETUP-007` Upgrade rejects unsupported protocol major minor mismatch
- `SETUP-008` Backend selection chooses Spotify Direct
- `SETUP-009` Backend selection chooses Music Assistant
- `SETUP-010` Backend selection falls back with structured error
- `SETUP-011` Profile creation creates explicit personal profile
- `SETUP-012` Profile creation creates household profile
- `SETUP-013` Device pairing stores client type and device token
- `SETUP-014` Device pairing rejects wrong setup code
- `SETUP-015` Device pairing learns canonical ESP32 device id
- `SETUP-016` Backend linking stores only backend-owned credentials
- `SETUP-017` Music account linking requests required Spotify scopes
- `SETUP-018` Music account linking repairs revoked refresh token
- `SETUP-019` Restart restores configured entries without re-pair
- `SETUP-020` Restart restores profile resolver mappings
- `SETUP-021` Recovery clears stale pairing on 401 or 403
- `SETUP-022` Recovery rotates device token only through explicit re-pair
- `SETUP-023` Export excludes tokens prompts history memory and raw audio
- `SETUP-024` Import restores profiles without secret material
- `SETUP-025` Import rejects unsupported schema version

### PROFILE
- `PROFILE-001` Explicit Profile owns personal state
- `PROFILE-002` Explicit Profile switches across rich clients
- `PROFILE-003` Explicit Profile private session suppresses persistence
- `PROFILE-004` Household Profile isolates shared state
- `PROFILE-005` Household Profile is default for shared room display
- `PROFILE-006` Guest Profile does not expose personal history
- `PROFILE-007` Guest Profile writes only guest-safe transient state
- `PROFILE-008` Kids Profile enforces safe backend routing
- `PROFILE-009` Kids Profile avoids private adult recommendations
- `PROFILE-010` Shared Room Profile resolves ambient Pi display
- `PROFILE-011` Shared Room Profile survives backend restart
- `PROFILE-012` Fallback Profile resolves when no stronger signal exists
- `PROFILE-013` Fallback Profile returns structured error when missing
- `PROFILE-014` Profile switching updates active context only
- `PROFILE-015` Profile switching does not migrate existing history
- `PROFILE-016` Profile deletion clears profile-owned Music DNA
- `PROFILE-017` Profile deletion clears profile-owned Ask DJ history
- `PROFILE-018` Profile deletion preserves unrelated profiles
- `PROFILE-019` Profile rename preserves stable profile id
- `PROFILE-020` Profile rename updates user-facing labels
- `PROFILE-021` Profile export includes portable profile preferences
- `PROFILE-022` Profile export excludes OAuth and bearer tokens
- `PROFILE-023` Profile import preserves privacy mode
- `PROFILE-024` Profile import resolves name collision safely

### RESOLVER
- `RESOLVER-001` Explicit Profile wins over device mapping
- `RESOLVER-002` Explicit Profile invalid selection fails closed
- `RESOLVER-003` Device mapping wins over area mapping
- `RESOLVER-004` Device mapping persists across restart
- `RESOLVER-005` Voice Endpoint mapping wins over inferred room
- `RESOLVER-006` Voice Endpoint shared mapping avoids personal inference
- `RESOLVER-007` HA User hint resolves after endpoint and device signals
- `RESOLVER-008` HA User hint never exposes secrets in context
- `RESOLVER-009` Area mapping resolves shared room profile
- `RESOLVER-010` Area mapping loses to device mapping
- `RESOLVER-011` Room mapping resolves household context
- `RESOLVER-012` Room mapping handles unmapped room fallback
- `RESOLVER-013` Playback Zone mapping resolves preferred profile
- `RESOLVER-014` Playback Zone mapping avoids becoming identity
- `RESOLVER-015` Fallback returns configured default profile
- `RESOLVER-016` Fallback emits structured profile error when absent
- `RESOLVER-017` Failure records sanitized resolver trace
- `RESOLVER-018` Failure does not fall through invalid explicit profile
- `RESOLVER-019` Restart persistence restores resolver order
- `RESOLVER-020` Restart persistence preserves mapping metadata

### ASK_DJ
- `ASKDJ-001` Conversation stores profile-scoped exchange
- `ASKDJ-002` Conversation deduplicates client message id
- `ASKDJ-003` Conversation returns uniform response envelope
- `ASKDJ-004` History sync returns revision-bounded messages
- `ASKDJ-005` History clear increments clear revision
- `ASKDJ-006` History trim emits retention system message
- `ASKDJ-007` Continuity resumes on second client
- `ASKDJ-008` Continuity does not rely on client-local cache
- `ASKDJ-009` Roaming keeps profile context across Apple and Windows
- `ASKDJ-010` Roaming keeps shared context on Pi
- `ASKDJ-011` Private Session answers without writing profile memory
- `ASKDJ-012` Private Session hides personal history from shared devices
- `ASKDJ-013` Shared Profile conversation remains shared
- `ASKDJ-014` Shared Profile does not leak personal Music DNA
- `ASKDJ-015` Guest request uses guest-safe profile
- `ASKDJ-016` Guest request avoids personalization from personal profiles
- `ASKDJ-017` Backend restart preserves pending follow-up until expiry
- `ASKDJ-018` Backend restart preserves history revision
- `ASKDJ-019` Client restart reloads history from backend
- `ASKDJ-020` Client restart clears stale cache after clear revision
- `ASKDJ-021` Mixed client renders text-only response without old artwork
- `ASKDJ-022` Mixed client renders actions only when present
- `ASKDJ-023` Help intent returns categorized text-only options
- `ASKDJ-024` Retry repeats previous retryable playback request
- `ASKDJ-025` Good morning intent returns confirmation actions
- `ASKDJ-026` Sleep intent pauses playback directly
- `ASKDJ-027` Gibberish prompt uses neutral unknown fallback
- `ASKDJ-028` Prompt injection does not trigger device lookup or playback

### MUSIC_DNA
- `MUSICDNA-001` Read returns profile dashboard data
- `MUSICDNA-002` Read respects disabled opt-in state
- `MUSICDNA-003` Write records compact positive playback signal
- `MUSICDNA-004` Write is skipped during private session
- `MUSICDNA-005` Update refreshes compact Spotify profile snapshot
- `MUSICDNA-006` Update respects snapshot TTL
- `MUSICDNA-007` Reset clears profile knowledge
- `MUSICDNA-008` Reset preserves opt-in setting
- `MUSICDNA-009` Roaming shares backend-owned DNA across rich clients
- `MUSICDNA-010` Roaming does not copy DNA into clients
- `MUSICDNA-011` Household separation isolates personal and household DNA
- `MUSICDNA-012` Household separation protects shared devices
- `MUSICDNA-013` Private Session does not add listening knowledge
- `MUSICDNA-014` Private Session can still read allowed context
- `MUSICDNA-015` Export includes portable settings only
- `MUSICDNA-016` Export excludes raw listening history
- `MUSICDNA-017` Import restores opt-in setting
- `MUSICDNA-018` Import starts knowledge from empty when data absent

### DISCOVER
- `DISCOVER-001` Recommendations are informative by default
- `DISCOVER-002` Recommendations include playable actions only with Spotify URI metadata
- `DISCOVER-003` Recommendations reject unsupported Spotify URI type
- `DISCOVER-004` Feedback like writes compact positive signal
- `DISCOVER-005` Feedback like does not start playback by itself
- `DISCOVER-006` Feedback dislike writes compact negative signal
- `DISCOVER-007` Feedback dislike does not mutate queue
- `DISCOVER-008` Profile separation keeps recommendations scoped
- `DISCOVER-009` Profile separation prevents guest seeing personal picks
- `DISCOVER-010` Household recommendations use household profile context
- `DISCOVER-011` Household recommendations avoid personal history leakage
- `DISCOVER-012` Guest recommendations stay generic or guest-safe
- `DISCOVER-013` Guest recommendations do not persist personal DNA
- `DISCOVER-014` Backend switch preserves platform recommendation contract
- `DISCOVER-015` Backend switch reports unsupported action cleanly
- `DISCOVER-016` Backend switch does not rewrite profile identity

### TRACK_INSIGHT
- `TRACKINSIGHT-001` Generation returns backend-owned analysis fields
- `TRACKINSIGHT-002` Generation enriches genre from Spotify artist metadata
- `TRACKINSIGHT-003` Generation handles missing backend data honestly
- `TRACKINSIGHT-004` Refresh updates stale insight cache
- `TRACKINSIGHT-005` Refresh preserves client-authoritative field boundary
- `TRACKINSIGHT-006` Refresh does not compute client-local conclusions
- `TRACKINSIGHT-007` Generation includes visual profile without raw prompts
- `TRACKINSIGHT-008` Refresh respects private session persistence limits

### PLAYBACK
- `PLAYBACK-001` Command play recommendation requires explicit command
- `PLAYBACK-002` Command ask followup response executes pending action
- `PLAYBACK-003` Command set shuffle uses set_shuffle boolean
- `PLAYBACK-004` Command set repeat uses off track or context
- `PLAYBACK-005` Pause response may include Resume control action
- `PLAYBACK-006` Output selection returns Activeer or Actief labels
- `PLAYBACK-007` Album play keeps album and track metadata separated
- `PLAYBACK-008` Recent played query never mutates playback
- `PLAYBACK-009` Backend playback never exposes Spotify tokens to clients
- `PLAYBACK-010` DJ response plays on DJConnect device not Spotify Connect

### BACKEND
- `BACKEND-001` Spotify token refresh retries once after 401
- `BACKEND-002` Spotify refresh token rotation stores latest token
- `BACKEND-003` Spotify invalid grant tries newer stored tokens first
- `BACKEND-004` Spotify reauthorize repair hides raw token response
- `BACKEND-005` Spotify playlist scope includes playlist read private
- `BACKEND-006` Music Assistant backend honors shared platform envelope
- `BACKEND-007` Backend source switch preserves profile preferences
- `BACKEND-008` Backend unavailable returns structured non-secret error

### PRIVACY
- `PRIVACY-001` Diagnostics redact token password secret proof authorization
- `PRIVACY-002` Diagnostics redact prompt history memory and raw audio
- `PRIVACY-003` Evidence capture redacts personal history by default
- `PRIVACY-004` Request Context excludes tokens and raw audio
- `PRIVACY-005` Export excludes Ask DJ history unless explicitly allowed
- `PRIVACY-006` Shared profile does not reveal personal Music DNA
- `PRIVACY-007` Guest profile does not reveal personal Ask DJ history
- `PRIVACY-008` Private session suppresses new persistence
- `PRIVACY-009` Logs do not include full ESP event payloads
- `PRIVACY-010` Image proxy avoids direct external content URL loading

### LOCALIZATION
- `LOCALIZATION-001` Canonical locale set includes en nl de fr es
- `LOCALIZATION-002` Fallback to English is explicit
- `LOCALIZATION-003` Pairing errors are localized
- `LOCALIZATION-004` Spotify OAuth errors are localized
- `LOCALIZATION-005` Profile privacy errors are localized
- `LOCALIZATION-006` Shared profile copy is localized
- `LOCALIZATION-007` Private session copy is localized
- `LOCALIZATION-008` Release install copy respects locale contract
- `LOCALIZATION-009` Accessibility labels are localized where supported
- `LOCALIZATION-010` Protocol values remain untranslated

### CAPABILITIES
- `CAPABILITIES-001` Status advertises ask_dj_supported
- `CAPABILITIES-002` Status advertises ask_dj_voice_supported
- `CAPABILITIES-003` Status advertises voice_supported
- `CAPABILITIES-004` Status advertises ask_dj_audio_response_supported
- `CAPABILITIES-005` Capabilities include profile contract version
- `CAPABILITIES-006` Capabilities include request context support
- `CAPABILITIES-007` Clients do not infer support from version alone
- `CAPABILITIES-008` Unsupported capability degrades cleanly

### VOICE
- `VOICE-001` WAV upload uses HA Assist STT provider
- `VOICE-002` No STT provider returns supported no-provider error
- `VOICE-003` Voice PTT routes transcript through Ask DJ backend
- `VOICE-004` Voice response includes transcript and recognized_text
- `VOICE-005` STT failure returns 422 stt_failed
- `VOICE-006` Audio response auto generates TTS for voice input
- `VOICE-007` Audio response never suppresses TTS audio
- `VOICE-008` Text-only voice test does not execute playback parser

### HARDWARE
- `HARDWARE-001` ESP32 status sends client_type esp32
- `HARDWARE-002` ESP32 status sends firmware metadata
- `HARDWARE-003` ESP32 status 426 version mismatch does not clear token
- `HARDWARE-004` ESP32 pairing sends device language only for ESP32
- `HARDWARE-005` ESP32 settings update through device command API
- `HARDWARE-006` ESP32 OTA selects public firmware manifest automatically
- `HARDWARE-007` ESP32 mDNS advertises djconnect service
- `HARDWARE-008` ESP32 BLE writes only WiFi credentials
- `HARDWARE-009` ESP32 PTT uploads raw WAV with bearer token
- `HARDWARE-010` ESP32 never stores playback backend credentials

### NETWORKING
- `NETWORKING-001` Runtime discovery prefers device local_url
- `NETWORKING-002` Runtime discovery uses exact mdns service match
- `NETWORKING-003` Runtime discovery ignores setup-code hostname fallback
- `NETWORKING-004` Image proxy returns tokenized local route
- `NETWORKING-005` Central API uses per-install djci token
- `NETWORKING-006` Apple push disabled without bootstrap proof
- `NETWORKING-007` APNs relay proof does not leak into diagnostics
- `NETWORKING-008` Offline backend path returns structured degraded response

### RELEASE
- `RELEASE-001` HACS release includes manifest version
- `RELEASE-002` Release notes include compatibility notes
- `RELEASE-003` Firmware release manifest includes checksums
- `RELEASE-004` Release artifacts preserve MIT license position
- `RELEASE-005` Third party notices mention Spotify trademark
- `RELEASE-006` README legal section remains compact and accurate
- `RELEASE-007` Production artifact passes secret scan
- `RELEASE-008` Version metadata matches protocol compatibility

### EXPORT
- `EXPORT-001` Profile export includes selected preferences
- `EXPORT-002` Profile export excludes tokens
- `EXPORT-003` Profile export excludes raw prompts
- `EXPORT-004` Profile export excludes raw audio
- `EXPORT-005` Profile export records schema version
- `EXPORT-006` Profile export supports all five locales where surfaced

### IMPORT
- `IMPORT-001` Profile import validates schema version
- `IMPORT-002` Profile import resolves duplicate names
- `IMPORT-003` Profile import keeps imported state profile-scoped
- `IMPORT-004` Profile import rejects secret-bearing payloads
- `IMPORT-005` Profile import preserves opt-in setting
- `IMPORT-006` Profile import creates actionable error on malformed file
