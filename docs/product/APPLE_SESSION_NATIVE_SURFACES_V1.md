# Apple Session native surfaces v1

## Current successor scope — shared five-parameter settings

[Owner decision6214905647](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6214905647) and the [canonical consolidation contract](PROFILE_SESSION_SETTINGS_CONSOLIDATION_V1.md) supersede device-local voice/gender and Session-only default semantics for the selected contract2 successor. Persona, concrete voice, qualified gender, Mood and Presence roam per Profile/Session; each explicit accepted field choice automatically becomes its Profile default and applies now when a Session is active. Automatic Mood/provider fallback/reconnect does not change defaults. No global HA pipeline change or new source/provider rights.

The delivered contract1 behavior and its source/PR evidence below remain historical/frozen; do not silently reinterpret version1 or infer installed/native adoption. The bounded old-consumer migration and removal gate is explicit in the successor. Core implementation is local/unpublished; Apple/other consumer changes remain owning-lane work, no WIP takeover or automatic dispatch.

## Delivered contract1 and historical qualification

Status: documentary design; product implementation **Planned**.
Parent: `DJC-SESSION-ENTRY-LIFECYCLE-HISTORY-DESIGN-V1-20261012`.
Addendum: `DJC-APPLE-SESSION-NATIVE-SURFACES-DESIGN-V1-20261012`.
[Full C decision](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6131317807),
[combined pickup](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6131363097),
[existing Apple join](https://github.com/pcvantol/djconnect-app/issues/87#issuecomment-6131089343).

## Position, pins and authority

One Core-owned Session, several native ways to stay near it. Widgets glance
and open; Live Activity/Island represents Session identity and lifecycle;
shortcuts navigate or request explicitly qualified operations; Continuation
invites selectively. None is a second player, planner, archive or conversation.

Current source inventory is Core `e8bb982f148ac7a22b6991ee6f54d10188849ee0` and
Apple `11ecab47bff28eaf6d7231f63477d893c0e91cb7` (remote commit tree and blobs,
read 2026-10-12). Apple has independently changing local WIP; this document does
not select, modify or certify that candidate. No Swift, push or signing writes.
Keep [CMB-12 historical assessment](APPLE_NATIVE_SURFACE_CAPABILITY_ASSESSMENT.md)
and its old Core `4aff740f` / Apple `8df26973` pins unchanged. This new disposition
is not a retrospective rewrite of that evidence.

Core already owns native Moment delivery, symbolic Mood, presence,
history/search and Forecast. Their native controls/view adoption remain
separately qualified. [Entry/lifecycle](SESSION_ENTRY_LIFECYCLE_EXPERIENCE_V1.md)
and [history summary](SESSION_HISTORY_SUMMARY_V1.md) are new designs, not existing
capabilities. Refine the existing Native Surface Integration and independent
Continuation families in [renderer roadmap](RENDERER_EXPERIENCE_ROADMAP.md) and
[product roadmap](../../PRODUCT_ROADMAP.md); do not reopen completed producers.

## Experience by surface

All rich content below is conditional on a separately qualified surface grant.
Until then, useful neutral status/navigation is the full supported fallback.

| Surface | Intended content and action | Limits / fallback |
| --- | --- | --- |
| Small widget | Session status, DJ identity, Open Session; no Session → Start preparation | Neutral label/open; no miniature Flow, private chat or playback console |
| Medium widget | One readable valid short Moment OR Session direction; Open Flow / Ask DJ | No forced fact, local generation, last-general-answer substitution or carousel |
| Large widget | More room for one contribution and short authorized Forecast; open rich in-app view | No 15-minute storyboard, queue or private history-summary dump; omit art without rights |
| Island compact/minimal | Quiet Session indicator; qualified paused/waiting state; tap opens current Session | No moving wave during pause, invented counter or next-track countdown |
| Island expanded / Lock Screen Activity | One valid short contribution/direction and state; few typed navigation actions | Neutral privacy mode; not every app button, full chat or locally calculated Forecast |
| App icon, App Shortcuts, Spotlight, native controls | Open Session, start preparation, Ask DJ, Forecast, earlier Sessions where appropriate | Availability and each action qualified independently; no GET/navigation mutation |
| Mac | Native widgets, menus/navigation/shortcuts; qualify supported mirrored Activity presentation separately | No artificial Island or assumed iOS parity |
| Watch | Reference the separately Planned Moment-first/PTT companion and OS mirroring where supported | No Watch redesign/full archive or second invitation |

Control Center, Lock Screen and Action Button are possible host/SDK-specific
realizations of the same typed actions, not extra intelligence or automatic
lifecycle authority. No CarPlay product expansion is selected. Five languages
`en/nl/de/fr/es`, VoiceOver, Dynamic Type, keyboard, contrast and Reduce Motion
are acceptance requirements; truncation must retain meaning and attribution.

## State and update matrix

Session lifecycle, playback, connectivity/freshness and pending operation are
independent dimensions. Do not persist new lifecycle enums for surface labels.

| State | Widget / Activity outcome | Effects |
| --- | --- | --- |
| No Session | Widget opens preparation/general Ask DJ; no active Session Activity | No hidden start/play |
| Local preparation | Navigation state only | No active Session or Activity inferred |
| Core-confirmed opening | Bounded pending/confirmed opening state | Not yet playback success |
| Active playing | Current qualified contribution/direction and context | No private Horizon export |
| Active paused | Same Session; pause label, frozen progress, permitted Flow | Do not end solely because `isPlaying` is false |
| Active waiting / no music | Choose music / no music; same Session | Empty queue while playing does not prove natural stop |
| Stale / disconnected / background unknown | Neutral stale status; expired rich payload removed from own presentation | No guessed end, fresh photo or completed action |
| Ended / interrupted / replaced | End/invalidate own Activity when learned; open neutral state or authorized read-only history | No Runtime revival or automatic new Session |
| Revoked / other Profile | No personal content; invalidate own grants/cache when learned | No old-target fallback into general chat |
| User dismisses / OS times out / app closes | Only local surface stops | Session/music unchanged; no automatic Activity restart loop |

Original Moment/source/Forecast deadlines never extend on repaint, reconnect,
view toggle or settings change. Compare subject, generation and revision before
applying any update: a late old Session/Profile cannot overwrite the new one.
Reconnect coalesces the newest valid state, not missed banners or contributions.
User dismissal is respected until a separately explicit permitted presentation
request. Receiving end after offline period must converge safely.

## Typed navigation and control

Proposed closed action vocabulary (not current wire enums): `open_session`,
`open_flow`, `open_moment`, `open_forecast`, `open_session_ask_dj`,
`open_general_ask_dj`, `start_preparation`, `open_end_confirmation`,
`open_spotify`, `open_history`. Reuse existing action dispatch after inventory;
choose exact route/schema in the producer subset, not an unrestricted executor.

A target/ref is not a credential. Resolve under current installation/Profile
and ordinary device authorization before private content or any mutation.
GET/deep-link resolution only navigates. Unknown/deprecated action, expired
Moment/opportunity, wrong installation/Profile, missing/replaced Session and
cold/warm launch receive explicit neutral/recovery outcomes. Archive navigation
never reconstructs Runtime. Preserve Flow/Forecast scroll/search and the
unsent Ask DJ draft.

Start/end/replace direct native invocation remains Planned and depends on
A's exact producer contract and existing Apple lifecycle qualification. Safe
v1 opens preparation or end confirmation UI. Replacement uses the same bound
confirmation for Siri, shortcut and cold launch; Cancel has zero effects. End
never silently pauses. Open Spotify uses A's typed allowlist, not a shell.

During an active Session, explicit Session Ask DJ opens its revalidated composer;
explicit general Ask DJ remains general. Replaced/ended target does not silently
retarget the draft. Navigation sends no text, starts no microphone or TTS.

## Minimal projection and three rights boundaries

Proposed `djconnect-native-session-surface/1` is a bounded projection of existing
Core authorities, not a new Store/Runtime/Horizon. Required design fields:
`schema_version`, `surface_category`, `purpose`, `revision`, `as_of`,
`freshness`, temporary `subject_binding`, `display_basis`, `cache_policy`,
`retention_until`, `status`, optional qualified `short_copy`, `attribution`,
`expires_at`, and `navigation_action`. Binding is installation/Profile/Session/
generation/purpose scoped inside authenticated resolution; do not place private
IDs or credentials in external notification text. Exact transport and maximum
payload size require qualification before the capability is advertised.

| Boundary | Permitted basis | Default |
| --- | --- | --- |
| Foreground owner app | Existing authenticated rich content/display grants | Existing in-app richness under current rights |
| Passive widget / Activity / Lock Screen | Explicit rights for this purpose, persistence, OS snapshots, cache and possible locked display | Neutral state/navigation; no rich data copied merely from owner `no-store` response |
| External invitation | Separate Continuation consent and strictly category-only projection | Off until selected, opted in and qualified |

App Group/UserDefaults, `.privacySensitive` and sanitizing strings are not
server rights. Private questions, history metrics, DNA, raw provider payloads,
credentials and internal Planner/Horizon slots never enter this projection.
Do not promise instant deletion of offline OS-cached pixels; content requiring
hard instantaneous withdrawal is unsuitable for rich passive presentation.
Neutral content is a deliberate useful product state. Clear only owned expired
transient surface data, not user/Session archives or unrelated widget settings.

Presence controls Core proactivity, not alert/haptic frequency. Music-only still
allows manual Session/Forecast/Ask DJ; Presenter does not add an interruption
budget. Silence is neither unread content nor an error. Mood/Persona are
confirmed Session values, not local analysis or Watch numeric conversion.

Forecast remains mutable direction, not a Moment or historical fact: external
nominal ±15 minutes, delivered current-context validity ceiling 120 seconds,
currently qualified imagery **current only**. `contextual` and
`qualified_upcoming` roles are reserved, not emitted in v1. No countdown to an
unproved future artist or `queue[0]` promise. Existing foreground artist-art
provenance/attribution/expiry is not a widget cache grant. Keep the rich in-app
Forecast destination; later surface qualification preserves every claim and
original image-use deadline. Private history totals are not automatically
Spotlight, Lock Screen, widget or push content. Cast navigation/status requires
its own boundary; expose no Broadcast token, handoff code, device/Profile detail
or auto-Cast effect.

## OS and transport reality

Official Apple documentation read 2026-10-12:
[WidgetKit updates](https://developer.apple.com/documentation/widgetkit/keeping-a-widget-up-to-date/),
[ActivityKit](https://developer.apple.com/documentation/activitykit),
[Activity push](https://developer.apple.com/documentation/activitykit/starting-and-updating-live-activities-with-activitykit-push-notifications).
WidgetKit timelines/reload budgets are system controlled; WidgetKit push is an
additional mechanism, not a replacement or proof of real-time parity. Live
Activities receive app or their own ActivityKit push updates and do not fetch
HA content themselves. Activity push tokens are not general notification tokens.
Token rotation, stale dates and update/end semantics need actual qualification.
No progress-tick pushes, forced-refresh budget bypass or audio background-mode
abuse while Spotify owns playback.

| Mode | Required qualification | Current source evidence |
| --- | --- | --- |
| Foreground app → surface | Subject/revision/expiry and rights under app updates | Playback-local Activity basis only |
| Suspended/background | Actual permitted SDK/host execution and cache/expiry behavior | Not established by foreground tests |
| Disconnected stale | No refreshed deadlines, useful neutral fallback and delayed end convergence | Must be tested separately |
| HA → relay/APNs → Activity/widget | Correct token family, permitted minimal payload, consent, delivery/end/revocation | Existing general APNs registration is insufficient |

Separate API/SDK availability from physical surface support. ActivityKit's
framework metadata includes iOS/iPadOS 16.1+, while concrete surface behavior
and mirrored presentation need their own OS/host checks. Do not infer that this
old minimum enables every Island, iPad, Mac or Watch surface. Apple documents
Live Activity presentation on iPhone/iPad and paired Watch/Mac; native Mac
widgets/menus and iPhone Activity mirroring are distinct. No claim that Mac
cannot present an Activity, nor that mirroring equals direct Activity creation.
Starting by remote push versus updating/ending has different OS requirements;
revalidate implementation SDK/OS support. This documentary work grants no
push-to-start, broadcast channel, APNs key, entitlement or relay deployment.

## Separate Session Continuation

Preserve Planner → bounded temporary Opportunity → separate Continuation Policy
→ category-only Notification Projection → native presentation → authorized
open/revalidation. Moment ≠ Opportunity ≠ consent ≠ invitation ≠ read receipt.
Surface synchronization is separate from inviting the user back.

Externally invite **off by default** until separately selected/qualified and
opted in. Policy needs category consent, personal/shared context, recent
participation, quiet hours and permitted platform settings. Do not pretend to
read arbitrary Focus/sleep state. No invented numeric cadence, marketing,
streaks, app-closed trigger, track/Moment spam or reconnect burst. One bounded
opportunity is handled once with expiry, limited retry and cross-client dedup;
iPhone→Watch mirroring is not a second invitation.

Visible copy and remote payload are category-only, for example a contribution
is ready. No artist/track/album/art, Mood/direction, free Moment text, question/
answer, private Profile/room/device, provider reference or playback action.
Persona may use fixed safe five-language catalog copy, not generated push prose.
Open fetches current authorized content; expired/ended target becomes neutral.
User-requested answer-ready notification is a separate family.

Silent Activity updates also require their own minimal approved payload;
“silent” cannot smuggle private full-content to the cloud or bypass consent via
alert configuration. Reuse only a proven appropriate relay boundary; HA retains
content and policy authority. No new server/account/provider/cost route.

## Current legacy disposition

All rows refer to Apple source pin `11ecab47bff28eaf6d7231f63477d893c0e91cb7`.
[Widgets](https://github.com/pcvantol/djconnect-app/blob/11ecab47bff28eaf6d7231f63477d893c0e91cb7/Apps/DJConnectTrackInsightWidgets/DJConnectTrackInsightWidgets.swift),
[models](https://github.com/pcvantol/djconnect-app/blob/11ecab47bff28eaf6d7231f63477d893c0e91cb7/Sources/DJConnectCore/DJConnectModels.swift),
[app model](https://github.com/pcvantol/djconnect-app/blob/11ecab47bff28eaf6d7231f63477d893c0e91cb7/Sources/DJConnectUI/DJConnectAppModel.swift),
[Activity controller](https://github.com/pcvantol/djconnect-app/blob/11ecab47bff28eaf6d7231f63477d893c0e91cb7/Sources/DJConnectUI/TrackInsightLiveActivityController.swift),
[iOS handlers/plist](https://github.com/pcvantol/djconnect-app/tree/11ecab47bff28eaf6d7231f63477d893c0e91cb7/Apps/DJConnectIOS),
[Mac handlers](https://github.com/pcvantol/djconnect-app/blob/11ecab47bff28eaf6d7231f63477d893c0e91cb7/Apps/DJConnectMac/DJConnectMacApp.swift).
Disposition is a planned migration decision, not a modification in this slice.

| Existing source component | Disposition | Reason / future verification |
| --- | --- | --- |
| `DJConnectNowPlayingWidget` | KEEP | Independent music context without Session; test paused/no-session and old configured widget |
| `DJConnectQueueWidget` | KEEP | Independent explicit queue view; no new Session/count/next-track inference |
| `DJConnectPlaylistsWidget` snapshot/model identifier | KEEP model; no current standalone widget delivery claimed | `DJConnectPlaylistsWidgetSnapshot.widgetKind` exists, but the current WidgetBundle registers only NowPlaying, Queue, TrackInsight and AskDJ; do not invent a deployed playlists widget |
| `DJConnectTrackInsightWidget` | KEEP | Existing independent feature; qualify its own rights, never relabel as Session Moment |
| `DJConnectAskDJWidget` navigation | REUSE | Explicit general chat remains general; no microphone/send on open |
| `DJConnectAskDJWidgetSnapshot` prompt/response/context/track/artist cache | REPLACE rich passive snapshot with qualified neutral navigation by default; RETIRE unqualified last-response exposure | String sanitization is not privacy grant; clear only owned transient snapshot, preserve chat/history; test stale old cache/migration |
| `TrackInsightLiveActivityController` + `DJConnectLiveActivities` | REPLACE playback-derived identity/lifecycle for the selected Session experience; REUSE permitted native layout mechanics | Current fixed `djconnect-now-playing`, `isPlaying` guard, `pushType:nil`; no simultaneous duplicate NowPlaying+Session Activity for the same selected experience; preserve independent player |
| `djconnect://now-playing`, `queue`, `track-insight`, `ask-dj`, `discover`/`discovery`, `playlists` and current aliases | KEEP | Exact HomeScreenAction parser includes those targets and Dutch/legacy aliases; no alias mutates or reroutes general Ask DJ |
| HomeScreenAction `now-playing`, `ask-dj`, `track-insight`, `discovery`, `queue`, `playlists` | REUSE | Enum supports six actions; iOS plist declares the first five, not playlists; add Session targets separately with auth/cold-start tests |
| iOS notification tap handler | REUSE legacy handling; REPLACE unhandled Session-target fallback | Sets pending `.askDJ` after unhandled tap; invalid Session invitation must become neutral |
| macOS notification tap handler | REUSE legacy handling; REPLACE unhandled Session-target fallback | Activates app and opens `.askDJ` after unhandled tap; invalid Session target must remain neutral |
| App-model notification dispatcher | REUSE explicit `music_discovery_ready` / legacy Ask DJ behavior | Discovery event refreshes Discovery; other events refresh general Ask DJ history and return false. New Session invitations must not fall through this refresh/open behavior |
| Existing App Group snapshot stores / reload calls | REUSE mechanics only after purpose qualification | No blanket widget reset, private archive wipe or old response resurrection after ambient retirement |

No existing configured kind is silently removed/reset. Migration must preserve
standalone Now Playing/Queue/Track Insight/Playlists and old explicit links.
The removed Core ambient producer does not qualify residual passive cache.
Invalid session notifications are distinguished before legacy fallback; no
new generic notification executor.

## Planned dependencies and acceptance

| Subset | Necessary dependency / boundary |
| --- | --- |
| Surface projection/rights/state | Existing owner authorities and neutral purpose contract; no full history-summary or future Planner dependency |
| Typed navigation/control | Navigation can proceed on existing authenticated read contracts; direct lifecycle actions require A producer plus existing lifecycle qualification |
| Native widget/Activity/Island adoption | Surface contract + typed navigation; host/SDK evidence; reuse `SLICE::APPLE::DJ-PRESENCE-CONTROL`, `FORECAST::APPLE::VIEW`, `AMBIENT::APPLE::JOIN` only for their bounded enriched integrations |
| Continuation policy/consent | Independent existing Continuation parent; opportunity, consent/privacy and dedup before invitations |
| Quiet/alert transport qualification | Surface payload for quiet updates; separate Continuation consent for alert invitations; token-family and host-specific tests |
| Joint acceptance | Exact producer/native/transport receipts for selected subset; no inferred installed/hardware PASS |

Do not require full B, future intelligence, Interactive DJMoments, Watch redesign
or physical Cast/LG acceptance for useful neutral navigation. Enriched controls
and Forecast routes retain their own planned consumer pins, not duplicate
assignments or hard prerequisites for every surface. Direct lifecycle qualifies
through existing `PROJ::QUAL::CMB12-LIFECYCLE`; category invitations do not merge
into Native Surface Integration.

Acceptance must cover noSession/preparation/opening/playing/paused/waiting/stale/
ended/interrupted/replaced/revoked; original expiry and 120s Forecast ceiling;
late old-target updates, missed end, reconnect coalescing, user dismissal;
cold/warm launch, other HA/Profile, malformed/expired refs, idempotent confirm/
cancel and archive-no-revival; preserved scroll/search/draft, explicit general
versus Session Ask DJ and no microphone/send; Music-only versus Presenter and
Silence; safe migration of every table row; OS cache/App Group/Spotlight/log
privacy, suspended/terminated/locked/offline modes; APNs token separation and
cross-client/Watch dedup. Five-language accessibility/layout tests and actual
host SDK/OS readbacks are required for later native delivery. This documentary
slice establishes none of those product, installed, APNs or hardware passes.

## Documentary delivery receipt

[Source PR #1160](https://github.com/pcvantol/djconnect/pull/1160) protected merged as `fdc79c9d7174b9d67dcf743400fbb76a0c163387`.
[Exact source/artifact qualification](../verification/SESSION_ENTRY_LIFECYCLE_HISTORY_DESIGN_V1_SOURCE_READBACK.md) records documentary checks and independent review; all proposed product implementation remains **Planned**. Separate Finalization reconciliation is still gated.


## Shared reactive dialogue and bounded Moment drilldown

The selected [common Ask DJ contract](ASK_DJ_CONTEXTUAL_DIALOGUE_CONTRACT_V1.md)
uses the existing conversation owner for both screens; optional Session/Moment
context does not create a second pipeline. The [Moment Track Insight subset](MOMENT_TRACK_INSIGHT_DRILLDOWN_V1.md)
adds an exact, temporary owner read through the existing full detail service.
This is one bounded connected correction; full interactive/narrative maturity,
native adoption, entry/lifecycle and joint acceptance remain independently Planned/open.
No model/provider lookup occurs merely by rendering a navigation offer.


## Apple Session surfaces consolidation request — 2026-10-15

User explicitly supersedes the legacy KEEP disposition for the Apple widget
experiences: one Session-only system across widgets, Live Activity and Dynamic
Island. Artwork and the current DJ Moment are primary; larger surfaces also show
track, artist and album. A newly admitted contribution updates the same surface,
without creating a second activity. No active Session means no active Activity;
configured widgets remain neutral and open the app. Existing widget kinds need
migration compatibility, not independent data stores or intelligence.

This request does not qualify the proposed passive-surface projection. Existing
native_delivery v1 and Session media no-store owner-display grants do not permit
App Group / WidgetKit / ActivityKit snapshot retention. Core producer work must
supply purpose-scoped passive display and image-cache rights, subject/generation
binding, immutable expiry, attribution, revocation/end semantics, and separately
qualify ActivityKit updates while the app is suspended (general APNs registration
is insufficient). Until the producer is qualified, Apple can consolidate neutral
status/navigation and retire legacy rich caches, but must not export owner-only
Moment/media payloads or claim real-time/background acceptance. Do not extend
source deadlines on local repaint or infer Session end from playback pause.

This is a user-requested design refinement and an explicit producer dependency,
not assignment, producer delivery, permission to alter the current Core writer,
or an installed/hardware acceptance receipt.


Current selected implementation: [Passive Session projection v1](PASSIVE_SESSION_PROJECTION_V1.md). Admission base9faffe533d4a117eb8ad362e73809d126bdcc9d7, same Core writer, branchcodex/passive-session-projection-v1; ACK6214264273. This reconciles only the preserved38-line relevant design delta; the original stash/recovery remains. Source, native rich, background, Watch and joint acceptance stay separate.
