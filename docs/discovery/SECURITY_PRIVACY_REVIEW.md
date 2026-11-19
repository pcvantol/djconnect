# Security and Privacy Review

## Summary

Security and privacy posture is strong in source repos and weaker in release-only documentation hygiene.

## Strengths

- HA diagnostics redaction is explicit and tested.
- Central API stores install tokens as hashes and encrypts APNs token material.
- ESP32 does not compile WiFi, HA or playback-backend credentials.
- Apple/Windows/Pi clients do not own Spotify credentials or durable Music DNA.
- Public workflows generally avoid secrets except dedicated deploy/release jobs.

## Risks

- Profile privacy cannot be fully enforced until Profile Architecture exists.
- Shared devices such as Pi/VibeCast need profile-aware privacy rules before personal surfaces expand.
- Central API is a high-sensitivity boundary and needs ADR-0007 before future cloud/profile work.
- Website operator functions must remain server-side and never expose relay/operator secrets.
- Release READMEs with stale token/storage wording can mislead users and support.

## Recommendations

1. Treat Profile Architecture as a privacy prerequisite for shared-device Personal features.
2. Add shared-device privacy tests after Profile resolver implementation.
3. Accept ADR-0007 before entitlement/cloud expansion.
4. Refresh release repo READMEs to current token/storage language.
5. Keep diagnostics and fixture tests checking for raw prompts, raw audio, tokens, history and Music DNA dumps.
