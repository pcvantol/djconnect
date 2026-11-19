# Presence policy2 consumer contract

Current local producer fixture, not an installed or released pin. The normative
mapping and server policy are in `docs/product/DJ_PRESENCE_FOUR_LEVELS_V2.md`.

- Read `active_session_presence.version=2` and exact four-value array in
  `capability.json`. The old five-value/version1 strict check needs an explicit
  version2 branch; do not silently accept a fifth selectable state.
- `transport_contract_version=1` describes the unchanged six-field legacy
  Presence POST. Primary Profile/Session settings transport stays contract3.
- The only deprecated input alias is `talkative -> presenter`, normalized by
  Core. Clients retain historical decoding, never invent a local selection.
- `runtime-publication-trace.json` records actual common Runtime publication
  against one source-shaped synthetic trace. Counts0/2/4/8 are observations in
  that trace, not targets or a promise for every720-second Session.
- These fixtures prove neither native adoption, installed state nor audibility.
  The source/producer pin follows protected delivery of the combined candidate.

Owning verification: `tests/test_presence_four_levels.py`,
`tests/test_session_presence.py`, `tests/test_profile_dj_settings_persistence.py`.
The fixed61-second SI-GOLDEN-002 mechanical scenario explicitly selects Presenter;
ordinary Runtime/Profile defaults remain Balanced. All four policies are separately
exercised by the rich publication trace and rolling/track/read-time fences.
