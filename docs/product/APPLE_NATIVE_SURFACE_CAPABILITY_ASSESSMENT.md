# CMB-12 — Apple Native Surface Capability Assessment

**Status:** Assessment complete

**Decision:** `GO_CMB12_APPLE_NATIVE_SURFACES_PARTIALLY_QUALIFIED`

**Scope:** Repository-first capability inventory of the canonical platform at
`djconnect` `4aff740fe9a96698a15fcb48c1199f16724aa5d8` and the Apple Renderer
Host at `djconnect-app` `8df26973fce788cac29cc8d8ab925781ee2ef63e`. This is
an assessment only: it adds no iOS, macOS or watchOS code; no Runtime, API,
Renderer, roadmap or Execution Horizon behavior; and no implementation
authorization.

## Canonical boundary

Native Surface Integration is a Renderer Host presentation family. Home
Assistant remains the sole owner of Profile/privacy, Session Runtime, Planner,
Knowledge, DJMoments, Session Flow, Presentation, Broadcast and command
authorization. A native surface may either open a local renderer view or submit
an explicit, already-authorized Session lifecycle request. It must not create
Runtime state, control playback autonomously or derive DJ intelligence.

The three canonical categories are unchanged:

| Category | Existing-boundary purpose | Ownership |
| --- | --- | --- |
| Session Control | Explicitly open an existing renderer view or submit an existing authorized Session request. | Apple Renderer Host locally; Runtime remains the request owner. |
| Session | Present an active Session only from existing renderer-safe projections, and remove the surface when that Session ends. | Apple Renderer Host presentation. |
| Information | Persistently present bounded renderer-safe information; never a second player or Runtime source. | Apple Renderer Host / Widget extension presentation. |

## Repository evidence and inventory

| Apple native surface | Status | Category | Objective evidence and disposition |
| --- | --- | --- | --- |
| Widgets | Supported | Information | `Apps/DJConnectTrackInsightWidgets` contains multiple `WidgetConfiguration` implementations and renderer-local `djconnect://` links. Existing widgets are Apple presentation evidence, not a new Session/Current-DJMoment projection contract. |
| Live Activity | Supported | Session | `TrackInsightLiveActivityController` creates, updates and ends the single local Activity only while playback is active; the widget extension supplies its Activity configuration. |
| Dynamic Island | Supported | Session | The existing Live Activity configuration renders expanded, compact and minimal `DynamicIsland` regions from the same bounded local state. |
| Lock Screen Live Activity | Supported | Session | The existing Activity configuration supplies the Lock Screen presentation. It is tied to the same active-playback lifecycle and is removed on end. |
| App Icon context menu | Supported | Session Control | `Apps/DJConnectIOS/Info.plist` declares Now Playing, Ask DJ, Track Insight, Discover and Queue actions; `DJConnectIOSAppDelegate` routes them through `DJConnectHomeScreenAction`. These open existing client surfaces only. |
| Custom application links | Supported | Session Control | `DJConnectHomeScreenAction` accepts the `djconnect://` scheme and existing targets; the iOS delegate and root view route those links to the same local actions. |
| Share Sheet | Supported | Information | `TrackInsightShareRenderer`, `TrackInsightShareService` and `ShareLink` are the completed CMB-11 Track Insight path. It remains explicit user sharing, not a Session-control or Session-continuation mechanism. |
| Notifications | Partial | Information | iOS, macOS and Watch register and handle remote notifications; the existing local notification path is Ask DJ-focused. No CMB-12 Session Continuation notification projection or policy is established. |
| Watch interactions and complications | Supported, separate | Information | The Watch app and `DJConnectWatchComplications` contain current Watch/WidgetKit evidence. They are evidence for the separately registered Apple Watch Moment-First Companion and do not select or qualify that capability here. |
| App Shortcuts / App Intents / Siri | Absent | Session Control | No `AppIntent`, `AppShortcutsProvider`, `INIntent` or SiriKit implementation is present. No lifecycle action is inferred. |
| Spotlight | Absent | Session Control | No Core Spotlight searchable-item implementation is present. |
| Universal Links | Absent | Session Control | No associated-domains entitlement or `applinks:` configuration is present. The existing custom URL scheme is not Universal Links evidence. |
| Handoff | Absent | Session Control | No `NSUserActivity` / Handoff implementation is present. |

This inventory is intentionally Apple-specific. CMB-07 establishes that Watch,
widgets, Live Activity and Share Sheet are platform-only realizations; their
presence creates no Windows parity requirement, and absent Windows-native
surfaces create no Apple work.

## Existing Session-control boundary

The only source-proven local control targets are Now Playing, Queue, Ask DJ,
Track Insight, Discover and Playlists. They open or navigate within existing
Apple renderer surfaces. The platform architecture permits only existing
authorized Start Session, Continue Session, Open Current Session, Open Ask DJ
and End Session requests for a future Session-control surface; it does not
prove a new native invocation for any of them. In particular, CMB-12 does not
authorize playback control, automatic Session mutation or a new intent.

## Session and information projection boundary

Existing Live Activity, Dynamic Island and Lock Screen presentation is bounded
to local renderer-safe current-playback state and ends when that state ends.
The canonical future Session-surface boundary remains existing renderer-safe
Session Direction, compact Session projection or Current DJMoment only when a
separate contract establishes the relevant projection. CMB-07 already records
that neither rich client has an explicit Current DJMoment renderer surface.

Existing widgets, the Track Insight Share Sheet and notifications cannot carry
or infer more than a renderer-safe, locally qualified payload. They must never
directly expose Music DNA, Profile or shared-profile data, Ask DJ history,
provider payloads, credentials/tokens, Planner/Knowledge/Runtime context,
internal identifiers, full queue or any sensitive Session-continuation content.
Lock Screen, widget, Live Activity and notification content remains concise and
content-neutral until the appropriate projection and privacy qualification
exists.

## Separate capability families

Apple Watch remains the separately registered Moment-First Companion: its app
and complication sources are inventory evidence only. Session Continuation
remains separately registered; current notification registration does not
establish continuation delivery, invitation, opening or revalidation. Interactive
DJMoments likewise remains unselected; a native surface can only later be a
renderer entry point for an independently authorized interactive projection.
None gains local intelligence, Session ownership or automatic playback from
this assessment.

## Remaining qualification items

1. **Rich-renderer active-Session contract disposition** — retained from
   CMB-07: decide whether renderer-safe Session Flow, Session Direction and
   Current DJMoment are shared, divergent or separately selected projections.
   This is required before a native surface can claim a new canonical Session
   or Information payload.
2. **Apple Session-control lifecycle invocation qualification** — identify the
   existing authorized lifecycle request and its privacy/authorization boundary
   before selecting any App Intent, Siri, Spotlight, Handoff or Universal Link
   delivery. Existing App Icon and custom-link navigation is not such evidence.

Both are Future Assessments. They do not authorize an implementation, alter the
Execution Horizon or create a new capability family. Once their independent
evidence is selected, separately bounded candidates may be assessed for an App
Intent/Siri control surface, a richer Session/Information surface, or a
notification presentation. No candidate is selected here.

## Qualification conclusion

The Apple Renderer Host has a substantial, objectively evidenced native-surface
base and its ownership is clear. It is only partially qualified because the
canonical active-Session projection disposition and lifecycle-invocation
evidence needed for new native surface delivery are not yet established. The
correct result is `GO_CMB12_APPLE_NATIVE_SURFACES_PARTIALLY_QUALIFIED`; it is a
GO for the completed inventory, not an implementation GO.

## Sources

- [Renderer Experience Roadmap](RENDERER_EXPERIENCE_ROADMAP.md)
- [Apple–Windows Atomic Convergence Assessment](APPLE_WINDOWS_ATOMIC_CONVERGENCE_ASSESSMENT.md)
- [DJConnect Capability Model](../../DJCONNECT_CAPABILITY_MODEL.md)
- [Product Roadmap](../../PRODUCT_ROADMAP.md)
- `djconnect-app` `Sources/DJConnectUI/TrackInsightLiveActivityController.swift`,
  `Apps/DJConnectTrackInsightWidgets/DJConnectTrackInsightWidgets.swift`,
  `Apps/DJConnectIOS/Info.plist`, `Apps/DJConnectIOS/DJConnectIOSApp.swift`,
  `Sources/DJConnectUI/DJConnectAppModel.swift`,
  `Sources/DJConnectUI/TrackInsightShareRenderer.swift`,
  `TrackInsightShareService.swift`, `TrackInsightShareViews.swift`,
  `Apps/DJConnectWatch/` and `Apps/DJConnectWatchComplications/` at
  `8df26973fce788cac29cc8d8ab925781ee2ef63e`.
