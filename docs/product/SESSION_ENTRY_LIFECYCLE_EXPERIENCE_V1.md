# Session entry and lifecycle experience v1

Status: documentary design; all new product implementation **Planned**.
Assignment: `DJC-SESSION-ENTRY-LIFECYCLE-HISTORY-DESIGN-V1-20261012`.
Owner: [full A/B decision](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6131072407),
[consolidation](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6131135945),
[pickup including C](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6131363097).
Source baseline: Core `e8bb982f148ac7a22b6991ee6f54d10188849ee0`;
Apple `11ecab47bff28eaf6d7231f63477d893c0e91cb7`, source inventory only.

## Authority and existing contracts

Core owns Session identity, authorization, lifecycle, observation and effects.
Apple owns navigation, selection and honest presentation. Runtime, Planner,
Knowledge, Moment Engine and Flow/Broadcast keep their existing ownership.
A view, voice transcript, app launch or external-app return cannot create a
Session fact. No second planner, generic command executor or new lifecycle
state is introduced by this document.

Reuse [persistent lifecycle](../../PERSISTENT_SESSION_ARCHITECTURE.md),
[Runtime contracts](../../DJ_SESSION_RUNTIME_CONTRACTS.md),
[Session conversation/history](SESSION_CONVERSATION_HISTORY_CONTRACT.md),
[observation](LIVE_PLAYBACK_OBSERVATION.md),
[Continue qualification](CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md),
[Mood](ACTIVE_SESSION_MOOD_V1.md), [presence](DJ_PRESENCE_V1.md) and
[Forecast](SESSION_FORECAST_V1.md). This design complements
[history summary](SESSION_HISTORY_SUMMARY_V1.md) and
[native surfaces](APPLE_SESSION_NATIVE_SURFACES_V1.md).

| Capability at the source baseline | Delivered basis | Remaining contract / qualification |
| --- | --- | --- |
| Owner start/read/end | Paired device → Profile → Session authority; `async_handle_session_start_payload`; existing one-active-session guard returns conflict | Explicit preparation/readiness projection and compound selection outcome; replacement confirmation and idempotent operation contract |
| Lifecycle | `OPENING`, `ACTIVE`, `ENDED`, `INTERRUPTED`; restart interrupts durable unfinished sessions | User experience reconciliation; no UI enum written into the Store |
| Spotify observation | Stage 1 accepted media-identity changes | Backend-owned occurrence identity and Stage 2 Continue remain blocked; no progress/URI heuristic |
| Manual / Discover / Exploring | Existing selected strategy and qualified discovery context | Musicless Manual waiting and selection→start/play must be separately proved; do not infer their availability from labels |
| Ask DJ text/voice | Existing authenticated question and STT routes, confirmation/actions, user history | Explicit lifecycle intent semantics, exact-target confirmation and turn/end ordering |
| Native music navigation | Independent Now Playing, Queue, Playlists, Discover and explicit Ask DJ | Return-to-session and start-with-selection UX; no Swift implementation here |

The delivered start handler can emit an opening Moment. That is not proof that
musicless waiting, join-current-playback or atomic start-plus-play is already
qualified. Continue is offered only when its complete advertised producer
capabilities and occurrence evidence are qualified. Otherwise explain the
unavailable join and offer an explicit supported choice; never silently change
Continue into Manual. Do not gate explicit Ask DJ or Session control on Music
DNA opt-in.

## State model and first entry

Read four separate dimensions: authoritative Session lifecycle; playback and
readiness; observation/connectivity confidence; pending user operation. Labels
such as “paused”, “waiting”, “choosing music” and “stale” are derived display
states, not new persistent lifecycle enums. Local preparation exists only in
client navigation; a real waiting Session requires a confirmed Core start.

| Entry state | Visible context and action | Confirmed outcome |
| --- | --- | --- |
| Authorized active Session | Open existing Session; current state, Flow and Forecast | Read/open only; no second Session or music restart |
| No Session, verified music playing | Current track, artist, permitted art and output; join only if qualified | Explicit qualified start; no restart or queue mutation |
| No Session, verified paused | Current/last context labelled paused; Resume or Choose music | Separate explicit playback action; start success only after Core acknowledgement |
| No Session, no music | Prominent Playlists and Discover; secondary Queue, Now Playing, Open Spotify | Preparation and browsing only until explicit qualified start |
| Pairing invalid / backend missing | Re-pair / authorize backend using actual reported reason | No fictitious empty queue, no optimistic Session |
| Backend or HA unreachable / ambiguous status | Connection recovery and neutral unknown context; retry read | Do not claim no music, end or selection success |
| Core-confirmed Manual waiting, if qualified later | Same Session, “Choose music”; retain its settings and Flow | Music choice changes playback only through explicit action; observation updates the same Session |

Start preparation retains the proposed Mood, Persona, presence and music
selection locally. It does not populate Runtime or archived history. Cancel
preparation discards only that preparation; no Session end or playback action.

## Music selection and return

Reuse existing native views; expose an explicit Return to DJ Session action.
Preserve Flow/Forecast scroll anchors, search, composer draft, selection context,
Mood, Persona and presence. Browsing, tab switches and Back have zero playback
or Session effects. Discover navigation does not select the Discover strategy.

| Selection action | Intent and boundary |
| --- | --- |
| Play | Existing explicitly authorized playback action; does not silently create/replace a Session |
| Queue | Existing explicitly authorized queue action; does not start a Session or guarantee upcoming playback |
| Start DJ Session with this | Typed selected media URI/identity, source, output and rights become an opening anchor, not a copied future queue or a DJ claim of having selected later music |
| Open Spotify | External selection navigation; no Core play/start result inferred |

Only advertise a composite Start new + Play selection when its producer contract
exists. Otherwise offer the distinct supported operations and their actual
results. Following Play, “Music plays → Session” requires fresh Core confirmation;
do not pull the user out of the selection view on a launch acknowledgement.
Selection invalidated, missing output, lost permission, removed provider media
or changed Profile fails before ending the previous Session where possible.

## Replacement and explicit lifecycle operations

All entrypoints, including UI, Ask DJ, STT, shortcut and cold launch, use the same
Core boundary. Starting while a Session is active offers Keep current or End
current and start new. A conflict alone is not permission to replace.

Proposed operation envelope (not an implemented endpoint): `operation_id`,
`installation_binding`, authenticated `profile_binding`, `target_session_id`,
`expected_session_revision`, `runtime_generation`, typed `selection`,
`requested_effects`, and optional single-use `confirmation_ref`. References are
opaque, server-owned, purpose-bound, short-lived and non-credentials. Choose
and qualify the exact TTL during producer implementation; no arbitrary timeout
is promised here. Scope the idempotency key to actor/Profile/operation payload;
a different payload with the same key conflicts rather than replaying effects.

1. Resolve current authority and target; preflight selection/output/rights and
   supported operation capabilities. Generate a server-bound confirmation.
2. Cancel consumes no effect. Keep current reads/opens that Session. Confirm
   rechecks target/revision/generation/Profile, expiry and preflight.
3. Serialize against the one-active-session invariant. End only the bound old
   Session; create at most one successor. Two devices, a late Yes, retry or
   duplicate voice turn cannot end a newer Session.
4. Playback is a separate external effect: there is no cross-HA/Spotify atomicity
   guarantee. Record each actual effect and expose partial failure with safe
   retry/readback. Never revive an ended Runtime to undo a failed play/start.

Proposed result contains `operation_id`, `target_session_id`, optional
`successor_session_id`, `effects[]` with typed effect/result/reason, and the
current authoritative revision. A timeout is `outcome_unknown` until owner
readback, not success or a second operation. Retry the same operation, not a
fresh play. Store only the bounded operation evidence necessary for idempotency
in the existing lifecycle authority; no new historical provider archive.

| Request | Semantic outcome |
| --- | --- |
| Start a DJ Session | Normal preparation/start; clarify missing required selection or capability |
| Start with playlist X | Resolve qualified typed selection; clarify ambiguity; active Session requires exact replacement confirmation |
| End this Session | End exact authorized target, no implicit pause |
| Pause / stop the music | Playback control, Session remains active |
| Ambiguous “stop” | Clarify music versus Session; zero effects before answer |
| End Session and pause music | Two explicit effects; disclose each result, including partial success |
| End with no active Session | Neutral idempotent acknowledgement; no fabricated Session |
| Quoted, negated, historical or help request | Informational; no lifecycle/playback mutation |

Text and STT pass through the same existing Core intent/confirmation route.
No client parser guesses authority from wording. After confirmed start an Open
Session action navigates to the acknowledged target. It never sends a new
question, enables microphone or requests TTS merely by opening.

At end, an already accepted session conversation turn follows the existing
Store/turn boundary. An end acknowledgement belongs in the authenticated Ask
DJ response/user history allowed by the existing route, or in operation UI
readback. It must not append a late turn to the closed Session timeline. A
pending unaccepted turn targeting an ended/replaced Session fails neutrally;
preserve its draft and ask the user where to continue. Do not silently retarget
it to the successor or general chat.

## Open Spotify and return

Accept only a typed, validated `spotify:{track|album|artist|playlist}:id` or
matching `https://open.spotify.com/...` content URL; reject credentials, arbitrary
schemes, shell commands, tracker/shortener redirects and malformed identities.
Use modern [UIApplication.open](https://developer.apple.com/documentation/uikit/uiapplication/open(_:options:completionhandler:))
on iOS and [NSWorkspace](https://developer.apple.com/documentation/appkit/nsworkspace)
on macOS. Spotify documents [content links](https://developer.spotify.com/documentation/ios/tutorials/content-linking);
this design does not adopt its legacy opening example or tracking infrastructure.

| Result | UX and follow-up |
| --- | --- |
| App open succeeded | Selection opportunity, not proof of play, account or output |
| App absent | Offer validated HTTPS content link if supported; no hidden play |
| URL open failed / no action returned | Honest failure with Retry / choose another route |
| Other Spotify account/output or no return | Do not bind external selection to the Session; existing Session is unchanged |
| User returns | Fresh authenticated Core read; only confirmed observation updates music context |

## Active lifecycle, pause and recovery

| Condition | Session / Flow / Forecast behavior |
| --- | --- |
| Confirmed pause | Same active Session and settings; freeze progress; existing valid Flow remains. Forecast waiting/limited/stale follows original validity |
| Empty queue while track plays | Remain active; no invented natural-end claim |
| Reliably known natural stop | Offer Choose music or End Session; do not automatically end |
| No music with unknown cause | Neutral no-music state; do not call it queue completion |
| Buffering / observation disconnected | Unknown/stale context; no fabricated pause/end or fresh cards |
| External music starts/changes | Existing observation updates same Session; no duplicated first Moment |
| End / replacement / revoked access | Close own live grants and current-only assets; authorized history remains read-only |
| HA restart | Durable unfinished Session becomes interrupted according to existing contracts; never reconstruct its Runtime |
| Resume / reconnect | Current snapshot, no catch-up stack, budget reset or replay of missed cards |

Pause-specific proactive/in-flight policy is a **remaining producer
qualification**, not inherited from presence Off. It must suppress stale
clock-driven cards during confirmed quiet playback, recheck before publication
and avoid a burst on resume while keeping explicit Ask DJ available. Presence,
Mood and Persona remain independent. No arbitrary idle auto-end timer is
selected. These refinements do not complete the broader Lifecycle family or
require completed Session Continuation for a safe entry subset.

## Phases and acceptance

| Planned subset | Required evidence before delivery |
| --- | --- |
| Entry/readiness and navigation | State matrix under real authenticated routes; no mutation by read/toggle/Back; unsupported Continue/musicless Manual honest |
| Core lifecycle operations | Target/revision confirmation, dedup, concurrent replace, revocation, timeout readback and partial effects; one active Session |
| Ask DJ text/voice lifecycle | Common routing; negation/quote/help; ambiguity; cancel; end-turn boundary; no DNA opt-in dependency |
| Native lifecycle control | Existing Apple lifecycle qualification node plus producer fixtures; cold/warm launch, draft/scroll preservation |
| Pause/recovery and joint UX | Paused/unknown/natural-stop/restart; in-flight suppression, no resume backlog; owner and each consumer receipts separately |

Acceptance cases cover playing, paused, musicless, unavailable, wrong Profile,
expired confirmation, two devices, duplicate request, failure after end, failed
play after start, late STT response, external music, missing Spotify and no
external return. Five-language copy (`en/nl/de/fr/es`), VoiceOver, Dynamic Type,
keyboard/contrast/Reduce Motion remain consumer requirements. Native, installed,
APNs and hardware acceptance are not established by this documentary delivery.
