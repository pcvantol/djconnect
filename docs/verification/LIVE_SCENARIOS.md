# Live Scenarios

Status: Scenario catalog ready; execution pending.

Use these IDs in `VERIFICATION_REPORT.md`. Every scenario requires sanitized
evidence before it can move from NOT TESTED.

## 1. Installation

| ID | Scenario | Expected behavior | Status |
| --- | --- | --- | --- |
| I-01 | New HA installation installs DJConnect | Config flow loads, profiles can be created, no stale state exists | NOT TESTED |
| I-02 | Existing installation upgrades to Profile Platform | Existing pairing/backend behavior survives, profile migration path works | NOT TESTED |
| I-03 | Household setup creates household and personal profiles | Household, personal, guest/shared profiles can be represented | NOT TESTED |
| I-04 | Device linking | Apple, Windows, Pi and ESP32 link to intended profiles | NOT TESTED |
| I-05 | Backend selection | Spotify Direct and Music Assistant selectable according to configured support | NOT TESTED |
| I-06 | Music account linking | Personal/shared account paths link without exposing credentials | NOT TESTED |
| I-07 | Fallback behavior | Missing profile signal uses fallback or structured error | NOT TESTED |

## 2. Apple

| ID | Scenario | Expected behavior | Status |
| --- | --- | --- | --- |
| A-01 | Pair iOS/iPadOS | Device pairs, advertises `client_type`, receives capabilities | NOT TESTED |
| A-02 | Pair macOS | Same contract as Apple Intelligence Client | NOT TESTED |
| A-03 | Pair watchOS through iPhone/iPad proxy | Watch uses `client_type:"watchos"` and own device id | NOT TESTED |
| A-04 | Ask DJ | Uses resolved profile, persists history unless private | NOT TESTED |
| A-05 | Music DNA dashboard | Reads profile-scoped data only | NOT TESTED |
| A-06 | Discover | Backend-owned feed respects profile and backend capabilities | NOT TESTED |
| A-07 | Track Insight | Backend-owned insight, no client-side conclusion | NOT TESTED |
| A-08 | Profile switching | Explicit profile wins over device mapping | NOT TESTED |
| A-09 | Private Session | No personal persistence | NOT TESTED |
| A-10 | Capability discovery | UI relies on capabilities and contract versions | NOT TESTED |
| A-11 | Reconnect/app restart | Profile selection, cache and backend revision recover safely | NOT TESTED |

## 3. Windows

| ID | Scenario | Expected behavior | Status |
| --- | --- | --- | --- |
| W-01 | Pair Windows | Device id prefix and `client_type:"windows"` accepted | NOT TESTED |
| W-02 | Ask DJ parity | Same profile and history behavior as Apple | NOT TESTED |
| W-03 | Music DNA parity | Same profile-scoped dashboard contract as Apple | NOT TESTED |
| W-04 | Discover parity | Same backend-owned feed semantics as Apple | NOT TESTED |
| W-05 | Track Insight parity | Same backend-owned insight contract as Apple | NOT TESTED |
| W-06 | Profile switching | Explicit profile selection works | NOT TESTED |
| W-07 | Private Session | Same suppression behavior as Apple | NOT TESTED |
| W-08 | Capability discovery | No version guessing | NOT TESTED |
| W-09 | Reconnect/app restart | Recovers using backend state and capabilities | NOT TESTED |
| W-10 | Intentional differences | Differences documented and accepted | NOT TESTED |

## 4. Raspberry Pi

| ID | Scenario | Expected behavior | Status |
| --- | --- | --- | --- |
| PI-01 | Household Profile | Defaults safely to household/shared context | NOT TESTED |
| PI-02 | Guest Profile | Guest-safe display and controls | NOT TESTED |
| PI-03 | Personal Profile explicit link | Personal state visible only when explicitly linked | NOT TESTED |
| PI-04 | Shared UX | Ambient UI avoids personal-first assumptions | NOT TESTED |
| PI-05 | Readonly behavior | Ask DJ/history surfaces are read-only or limited as intended | NOT TESTED |
| PI-06 | Privacy | No personal history leakage on shared display | NOT TESTED |
| PI-07 | Cache isolation | Cached profile data does not cross profile boundaries | NOT TESTED |

## 5. ESP32

| ID | Scenario | Expected behavior | Status |
| --- | --- | --- | --- |
| E-01 | Pairing | `client_type:"esp32"` and model-specific device id accepted | NOT TESTED |
| E-02 | PTT | WAV upload reaches HA voice endpoint with device context | NOT TESTED |
| E-03 | Voice upload | STT/Ask DJ flow works or returns clear STT error | NOT TESTED |
| E-04 | DJ response | HA posts text/audio URL to `/api/device/dj_response` | NOT TESTED |
| E-05 | Device mapping | Resolver uses mapped device profile | NOT TESTED |
| E-06 | Profile resolution | ESP has no profile UI and owns no personal state | NOT TESTED |
| E-07 | Capability discovery | Pair/status advertises relevant support | NOT TESTED |
| E-08 | OTA unaffected | Firmware update flow still works | NOT TESTED |

## 6. Home Assistant Voice Endpoints

| ID | Scenario | Expected behavior | Status |
| --- | --- | --- | --- |
| V-01 | Voice request | Voice Endpoint request enters Request Context | NOT TESTED |
| V-02 | Area mapping | Area/room maps to shared/room/household profile | NOT TESTED |
| V-03 | Household Profile | Shared voice request uses household profile | NOT TESTED |
| V-04 | Fallback | Missing mapping falls back safely or errors clearly | NOT TESTED |
| V-05 | Playback routing | Playback target follows profile/backend/zone routing | NOT TESTED |
| V-06 | Ask DJ | Ask DJ works without personal history leakage | NOT TESTED |
| V-07 | Private Session | Private voice context suppresses persistence | NOT TESTED |
| V-08 | No identity guessing | Ambiguous speaker never resolves to personal profile by guess | NOT TESTED |

## 7. Mixed Scenarios

| ID | Scenario | Expected behavior | Status |
| --- | --- | --- | --- |
| M-01 | Apple -> Peter Profile -> Ask DJ -> Pi household | Pi does not reveal Peter personal history | NOT TESTED |
| M-02 | ESP -> Peter -> Music DNA update -> Apple | Apple sees new profile-owned state promptly | NOT TESTED |
| M-03 | Voice Endpoint -> Kitchen -> Household -> playback | Household context routes playback correctly | NOT TESTED |
| M-04 | Windows private Ask DJ -> Apple same profile | Private request absent from shared history | NOT TESTED |
| M-05 | Guest Profile on Pi -> Apple personal profile | Guest state does not contaminate personal profile | NOT TESTED |

## 8. Backend Restart

| ID | Scenario | Expected behavior | Status |
| --- | --- | --- | --- |
| B-01 | Restart Home Assistant | Profiles survive | NOT TESTED |
| B-02 | Restart Home Assistant | Mappings survive | NOT TESTED |
| B-03 | Restart Home Assistant | Resolver behavior survives | NOT TESTED |
| B-04 | Restart Home Assistant | Music Backend selection survives | NOT TESTED |
| B-05 | Restart Home Assistant | Cache survives or refreshes without corruption | NOT TESTED |

## 9. Backend Switching

| ID | Scenario | Expected behavior | Status |
| --- | --- | --- | --- |
| BS-01 | Spotify Direct -> Music Assistant | Same Profile remains active | NOT TESTED |
| BS-02 | Spotify Direct -> Music Assistant | Same Music DNA remains visible where backend supports data | NOT TESTED |
| BS-03 | Spotify Direct -> Music Assistant | Same Ask DJ history remains visible | NOT TESTED |
| BS-04 | Stale backend action | Returns `stale_backend_action` or capability-safe error | NOT TESTED |
| BS-05 | Unsupported capability | Returns `unsupported_backend_capability` without vague 500 | NOT TESTED |

## 10. Export / Import

| ID | Scenario | Expected behavior | Status |
| --- | --- | --- | --- |
| X-01 | Profile export | Non-secret profile state exported | NOT TESTED |
| X-02 | Household export | Profiles and mappings exported without secrets | NOT TESTED |
| X-03 | Full export | Integration export excludes credentials and tokens | NOT TESTED |
| X-04 | Import to fresh HA instance | Profiles and mappings restored | NOT TESTED |
| X-05 | Relink accounts | Provider accounts relink successfully after import | NOT TESTED |
| X-06 | Post-import usage | Ask DJ/playback/profile routing work | NOT TESTED |

## 11. Privacy

| ID | Scenario | Expected behavior | Status |
| --- | --- | --- | --- |
| PV-01 | Private Session | No history/Music DNA/recommendation persistence | NOT TESTED |
| PV-02 | Guest Profile | Guest-safe responses and exports | NOT TESTED |
| PV-03 | Household Profile | Shared state only | NOT TESTED |
| PV-04 | Shared Profile | No personal leak by default | NOT TESTED |
| PV-05 | Personal Profile | Personal state visible only to resolved profile context | NOT TESTED |
| PV-06 | Logs/diagnostics | Secret and personal data redacted | NOT TESTED |

## 12. Capability Discovery

| ID | Scenario | Expected behavior | Status |
| --- | --- | --- | --- |
| C-01 | Apple capabilities | Detects Profile Platform, Request Context, Private Session, Export and versions | NOT TESTED |
| C-02 | Windows capabilities | Same as Apple where supported | NOT TESTED |
| C-03 | Pi capabilities | Detects shared/ambient capability subset | NOT TESTED |
| C-04 | ESP32 capabilities | Detects device/voice/control support without profile ownership | NOT TESTED |
| C-05 | Voice Endpoint capabilities | Backend advertises Voice Endpoint request context/mappings | NOT TESTED |
| C-06 | Version behavior | No client guesses support from version strings | NOT TESTED |

## 13. Performance

| ID | Scenario | Metric | Status |
| --- | --- | --- | --- |
| PF-01 | Resolver overhead | Added latency per request | NOT TESTED |
| PF-02 | Extra API calls | Count per common workflow | NOT TESTED |
| PF-03 | Profile switching latency | Time from selection to resolved request | NOT TESTED |
| PF-04 | Ask DJ latency | End-to-end by backend/profile/private mode | NOT TESTED |
| PF-05 | Music DNA latency | Profile dashboard load/update time | NOT TESTED |
| PF-06 | Cache efficiency | Hit rate and unexpected repeated requests | NOT TESTED |

## 14. Regression

| ID | Scenario | Expected behavior | Status |
| --- | --- | --- | --- |
| RG-01 | Playback | Existing playback commands still work | NOT TESTED |
| RG-02 | Volume | Volume controls still work | NOT TESTED |
| RG-03 | Player selection | Output/player selection still works | NOT TESTED |
| RG-04 | Discovery | Discovery still works according to backend capabilities | NOT TESTED |
| RG-05 | Track Insight | Existing Track Insight still works | NOT TESTED |
| RG-06 | ESP firmware | Pairing, status, voice and OTA still work | NOT TESTED |
| RG-07 | Pi UI | Ambient UI still works | NOT TESTED |
| RG-08 | Apple UI | Existing Apple UI still works | NOT TESTED |
| RG-09 | Windows UI | Existing Windows UI still works | NOT TESTED |
