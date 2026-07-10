# Profile Platform Verification

Status: Evidence pending  
Baseline: Profile Platform v1  
Contract: `docs/implementation/epic3b/01-profile-adoption-contract.md`

## Invariants To Prove

| Invariant | Expected proof |
| --- | --- |
| Profile is durable identity | Music DNA, Ask DJ history, preferences and backend routing follow the resolved Profile across Apple, Windows and backend surfaces. |
| Request Context is canonical input | Apple, Windows, Pi, ESP32, Voice Endpoint, services, REST and websocket requests route through the canonical resolver signals. |
| Resolver order is deterministic | Explicit profile wins, device mapping beats area, Voice Endpoint mapping beats inferred area, invalid explicit profile fails. |
| Devices do not own personal state | ESP32 and Pi device state never becomes Music DNA or personal Ask DJ ownership. |
| Voice Endpoints do not guess identity | Shared voice requests resolve through configured mapping, area/room or fallback and do not infer a personal profile. |
| Private Session suppresses persistence | Ask DJ, Music DNA, recommendations, likes/dislikes and mood changes are not persisted from private-session requests. |
| Capability discovery is authoritative | Clients discover `profiles`, `request_context`, `private_sessions`, `profile_export` and contract versions before enabling UI. |
| Export/import is non-secret | Exports exclude OAuth, HA, APNs and device tokens and imports reject secret-like fields. |

## Required Capability Response

Clients must verify support through `djconnect/capabilities` and equivalent
pair/status metadata where applicable:

```json
{
  "capabilities": {
    "profiles": true,
    "explicit_profile_selection": true,
    "private_sessions": true,
    "profile_export": true,
    "request_context": true,
    "voice_endpoint_request_context": true,
    "voice_endpoint_mappings": true
  },
  "contract_versions": {
    "profile_context": 1,
    "client_contract_fixtures": 1
  }
}
```

## Resolver Verification Matrix

| ID | Input context | Expected resolution | Status |
| --- | --- | --- | --- |
| R-01 | Valid explicit `profile_id` plus conflicting `device_id` | Explicit profile | NOT TESTED |
| R-02 | Invalid explicit `profile_id` plus valid mapped device | `invalid_profile`; no fallback | NOT TESTED |
| R-03 | Mapped Apple/Windows device | Device-linked profile | NOT TESTED |
| R-04 | Mapped ESP32 device | Device-linked profile, no ESP ownership of personal state | NOT TESTED |
| R-05 | Explicit Voice Endpoint mapping | Mapped shared/room/household profile | NOT TESTED |
| R-06 | Voice Endpoint in mapped area | Area/room profile | NOT TESTED |
| R-07 | HA user hint only | Mapped user profile where configured | NOT TESTED |
| R-08 | Playback zone/player mapping | Zone profile where configured | NOT TESTED |
| R-09 | No usable signal with fallback configured | Fallback profile | NOT TESTED |
| R-10 | No usable signal and no fallback | Structured profile error | NOT TESTED |

## Profile State Verification

| ID | Scenario | Expected behavior | Status |
| --- | --- | --- | --- |
| P-01 | Ask DJ from Apple as Peter | Response and history stored under Peter Profile | NOT TESTED |
| P-02 | Same history loaded from Windows as Peter | Same profile history visible | NOT TESTED |
| P-03 | Pi household view after Peter Ask DJ | Personal history not visible by default | NOT TESTED |
| P-04 | ESP32 PTT mapped to Peter | Profile-scoped Music DNA may update, ESP stores no history | NOT TESTED |
| P-05 | Private Session Ask DJ | No Ask DJ history or Music DNA persistence | NOT TESTED |
| P-06 | Guest Profile Ask DJ | Guest-safe response, no personal leakage | NOT TESTED |
| P-07 | Backend switch from Spotify Direct to Music Assistant | Profile, Music DNA and Ask DJ history survive | NOT TESTED |
| P-08 | Fresh HA import and account relink | Profiles/mappings restore without secrets | NOT TESTED |

## Privacy Verification

| ID | Check | Expected behavior | Status |
| --- | --- | --- | --- |
| PR-01 | Request Context logging | No tokens, raw prompts, raw audio, history or Music DNA contents | NOT TESTED |
| PR-02 | Diagnostics | Secret-like keys redacted and legal metadata present | NOT TESTED |
| PR-03 | Profile export | No provider, HA, APNs or device tokens | NOT TESTED |
| PR-04 | Household/full export | Non-secret household state only | NOT TESTED |
| PR-05 | Import with secret-like fields | Rejected, not silently stored | NOT TESTED |
| PR-06 | Shared/household profile on Pi | No personal Music DNA or private Ask DJ history | NOT TESTED |
| PR-07 | Voice Endpoint ambiguous context | No personal identity guessing | NOT TESTED |

## Localization Verification

| ID | Scenario | Expected behavior | Status |
| --- | --- | --- | --- |
| L-01 | Catalog validation | Required locale catalogs or native equivalents exist for `en`, `nl`, `de`, `fr` and `es` where user-facing copy exists | NOT TESTED |
| L-02 | Key completeness | All required catalogs contain the same required user-facing keys | NOT TESTED |
| L-03 | Placeholder consistency | Placeholder names, counts and formatting specifiers match across locales | NOT TESTED |
| L-04 | English fallback | Unsupported or regional locale variants fall back deterministically to English | NOT TESTED |
| L-05 | Raw-key smoke test | Rendered primary flows do not show raw localization keys | NOT TESTED |
| L-06 | Onboarding | Pairing/onboarding renders correctly in all five languages | NOT TESTED |
| L-07 | Profile/privacy errors | Profile-required, device-not-mapped, backend-not-configured and privacy/private-session errors render localized display messages while machine codes remain untranslated | NOT TESTED |
| L-08 | Shared and private contexts | Shared-profile, guest-profile and private-session copy is localized and privacy-safe | NOT TESTED |
| L-09 | Website | Website routes or locale switching, metadata, privacy/support pages and canonical terms are available and validated per locale | NOT TESTED |
| L-10 | Release/install copy | Release and install instructions intended for end users follow the five-language policy where multilingual release copy is present | NOT TESTED |

## Acceptance Criteria

Profile Platform verification passes when all resolver, state and privacy
checks above are PASS or a non-blocking WARNING accepted in
`KNOWN_LIMITATIONS.md`, and no privacy leak remains open.
