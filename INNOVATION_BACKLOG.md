# DJConnect Innovation Backlog

**Owner:** Innovation Lab
**Status:** Canonical active register

This register organizes research candidates. Detail remains in
`INNOVATION_LAB.md`. No item may begin production delivery from this register;
it follows `INNOVATION_PROMOTION_POLICY.md`.

| Initiative | Category | Priority | Status | Dependencies | Promotion path |
| --- | --- | --- | --- | --- | --- |
| Dedicated Music Search UX | Product Innovation | P1 | Innovation Lab | structured Ask DJ music-search capability, profile/privacy contract | Product Development only after explicit GO and promotion; then create a new owner and `Planned` or `Backlog` record |
| Lyrics Explain and Live Lyrics | AI Innovation | P2 | Innovation Lab | licensing, provider coverage and shared-display privacy | Product Development after research GO |
| VibeCast Guest Companion | Product Innovation | P2 | Innovation Lab | guest-session security and privacy review | Product Development after prototype evaluation |
| Audience Experience and Ambient Reactions | Product Innovation | P2 | Deferred | Audience Event privacy, Session participation policy, renderer pressure/aggregation and VibeCast feasibility; `docs/product/AUDIENCE_EXPERIENCE_ARCHITECTURE.md` | Bounded Product Development capability only after explicit GO; reaction intake, Audience Projection, VibeCast Audience Layer, optional Ambient Light response and any Audience Observation remain separately authorized |
| Ambient Client capability budget | Product Innovation | P2 | Innovation Lab | shared-profile and display privacy analysis | Product Development after architecture review |
| Profile portability | Product Innovation | P3 | Innovation Lab | export privacy and relinking model | Product Development after architecture review |
| VR/MR experiences | Research | P3 | Innovation Lab | client feasibility and product evidence | Product Development after prototype evaluation |
| Cloud Profile Sync and entitlements | Platform Innovation | P3 | Deferred | local-first and privacy evidence | Platform Evolution or Product Development after GO |
| Contract Fixture Compatibility Dashboard | Platform Innovation | P3 | Innovation Lab | verification and client conformance evidence | Platform Evolution after research GO |
| Foundation language lint | Platform Innovation | P3 | Innovation Lab | terminology policy and false-positive assessment | Platform Evolution after research GO |

## Dedicated Music Search UX boundary

This Innovation Lab candidate is not a delivery commitment. It reuses the
backend-owned Ask DJ music-search capability and the
existing music-backend and playback abstractions for Windows, iPhone/iPad and
macOS. Its dedicated request scope is limited to `music.search`,
`playback.play_selected` and eligible `music_dna.record_selection` events.
The backend must enforce that scope; the UI accepts only typed structured
results and fails closed for prose, chat content, unknown response types or
out-of-scope actions. Typed and editable speech input use the same contract.

An explicit, successful selection may be recorded only for the active profile
when Music DNA is enabled. Unsubmitted input, speech audio, unselected results
and failed searches are not preference signals. It becomes Product Development
work only after an explicit GO and promotion decision; that promotion creates a
new owner and a new `Planned` or `Backlog` status. This candidate is not a
second search backend, general Ask DJ UI, search history or provider-specific
client implementation.
