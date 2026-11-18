# Core dead and legacy route assessment — 17 October 2026

Scope:155 Core Python files,2396top-level definitions at local checkpoint
`40d1bea9f604d1905bdcb5f9651b70c9d03e647d`; remote main readback
`cc9b49fe9ca5312dd3bf962b3bac319aa25b3f15`. Assessment, not a removal or
installed acceptance claim. Existing worktrees/WIP remain untouched.

Fresh canonical hostverify exited0, MATCH, onboarding4.5.3. Static AST/name,
import-alias, registrations and actual call-site inspection produced63initial
unreferenced candidates. These include legitimate HA hooks and planned contracts;
63 does not mean63dead functions. Three behavioral differences below were
reproduced against actual handlers/SQLite in an isolated no-network HA test image.
Only external provider/model replies and owner identities were fixtures.

## Findings in priority order

| Priority | Route / evidence | Consequence and disposition |
| --- | --- | --- |
| P1 | `vibecast.py:async_handle_vibecast_payload` → `_generate_items` → `_generate_conversation_items`; registered HTTP/developer/tool paths | Still an independent text producer: a feed read can send current track/artist/album/genre to the model and return three `source.kind:conversation` items. Reproduction: HTTP-handler result200,1model-boundary call,3items, no Session Runtime manager. It does not obtain Session presence/budget/source-model admission. Consolidate behind existing qualified Session projection; preserve renderer/consumer compatibility and never merely rename the generator. No actual private data/model call occurred in this audit. |
| P2 | `api_handlers.py:async_handle_ask_dj_idle_suggestion_payload` → `ask_dj.async_idle_suggestion` → assistant-history append | Active separate system-message route, outside Planner/Moment semantic publication. Reproduction with an actual active `music_only` Runtime:200, history_revision1, assistant message, no Moment identity. Existing Apple source still contains an automatic caller (guarded by its screen scope); deployment/actual phone invocation not proven. Retire/converge the producer with an explicit compatible disposition; preserve old stored history. |
| P2 | `http.py:_play_now_fallback_dj_text` → `voice_profile_for_mood_or_config` | A second active tone selector remains for Play Now captions: incoming numeric Mood/old voice_profile selects a hardcoded caption, while confirmed Session Persona is used only for language here. Inspect and consolidate with the accepted shared settings/expression owner; do not remove the active command answer. This is source-path evidence, not a new installed UI reproduction. |
| P2, internal/dormant exposure | `historical_projection_query.py` old `async_get_session`, `async_get_owner_session`, `async_list_recent_owner_sessions`, `async_get_moment`, `async_list_session_moments` | Old projection readers check owner/version/visibility, bypassing current retention/history-enabled/source fences. Actual SQLite reproduction: old method returns an expired history-disabled Session; current `_session` denies it. No production HTTP caller to these old methods was found; do not label this an externally demonstrated leak. Remove unused public facades or route them through the canonical query owner before reuse. |
| P3 | Seven old backend sensor classes; `DJConnectVolumeNumber`, `DJConnectShuffleSwitch`, `DJConnectCommandButton`, `DJConnectRefreshUpNextButton` | Setup registers replacements/hardware controls and explicitly removes these old entity IDs. Constructors survive in tests but are not instantiated by product setup. Remove obsolete implementations and tests of retired behavior; retain registry cleanup keys/helpers and supported ESP controls. |
| P3 | `DJConnectAskDjClearView` and `API_ASK_DJ_CLEAR` | Old `/ask_dj/clear` view has no registration/import caller. Canonical registered `/ask_dj/history/clear` remains. Remove the abandoned implementation; never remove or redirect the active clear route without preserving its authority/revisions. |
| P3 | Ask DJ queue helpers `_queue_items_without_current`, `_empty_queue_response`, `_queue_response`, `_dedupe_queue_items`, `_playback_uri`, `_current_playback_uri` | Retained old branch beside the actual `observations.queue_read` route. Includes stale hardcoded Dutch text and URI dedup semantics. Verify dependent helper closure and remove dead branch, not the current queue owner. |
| P3 | `TrackInsightCoordinator`, `TrackInsightIntentHandler`, `TrackInsightHassService`; `session_conversation.async_session_exchange` | Unused/test-only compatibility facades. Current registered owners call canonical API/application services directly. Remove or explicitly deprecate these surfaces; retain actual Track Insight service and common dialogue. |
| P3 | `dj.parse_music_request`, `tts.create_tts_wav`, `tts.create_error_wav` | Disabled direct-AI stub and unused WAV-only/tone wrappers. Not the active generic HA TTS/speech path. Remove dead wrappers; retain `pipeline.py`, `wav_util.py` and supported ESP/Assist routes. |
| P3 | `voice_profile_style_text_for_payload`, `_STYLE_TEXT`, `mood_announcement_style_text`, `enrich_user_text_with_memory`, unused config-flow helpers and push wrappers | No product call to these selected entry points after alias inspection; some have unit tests. Remove only the verified closed dependency sets. The whole voice_profiles module is not dead: active Play Now/compatibility readers still exist. |

## Not removal findings

- `handle_spotify_command` is live through its `_handle_spotify_command` import
  alias in `use_cases.py`. Pair-code helpers also have active alias callers.
- HA discovers setup/migrate/remove/repair/diagnostic hooks and ConfigFlow classes;
  absence of ordinary Python calls is not proof of death.
- Windows retirement recognition, source-transfer fences, stored-key migration,
  entity-registry removal, supported HA-version STT adaptation and versioned
  storage migrations retain safety/compatibility functions.
- `credit_provenance.py` explicitly defines an unconnected Phase-A policy contract.
  Its limited Spotify-role scope is distinct from delivered CC0 recording credits.
  Reconcile planned-contract ownership before deleting it as supposedly legacy.
- Generic ESP TTS and configured Session speech share existing byte/settings
  owners but intentionally have different transport/auth contracts. Do not delete
  ESP/Assist compatibility merely because the newer Session endpoint exists.

## Public music research gap

The audited active Core contains no Wikipedia article fetch or DuckDuckGo web
research adapter. Required agent qualification disables autonomous provider web
search/tools; current general answers can therefore be model knowledge, not an
actual Wikipedia consultation. The old prompt's list of sources was not a fetch
receipt. The owner's new research direction is designed in
[Ask DJ public music research](../product/ASK_DJ_PUBLIC_MUSIC_RESEARCH_V1.md).

## Reproducible evidence and limits

The existing Core writer retains the AST candidate JSON and three isolated
handler/SQLite reproductions. No installed HA, network, Spotify playback,
provider settings, Apple source or secrets were modified. The source checkpoint
remains the reproducible baseline; forthcoming fixes require new exact reviews.
This audit does not convert metadata-only, test-only or framework-discovered
code into a blanket deletion list.
