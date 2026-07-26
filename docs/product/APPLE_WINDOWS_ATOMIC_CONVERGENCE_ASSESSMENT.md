# CMB-07 — Apple–Windows Atomic Convergence Assessment

**Status:** Assessment complete

**Decision:** `GO_CMB07_APPLE_WINDOWS_CONVERGENCE_PARTIALLY_QUALIFIED`

**Scope:** Repository-first comparison of the canonical DJConnect platform with
`djconnect-app` `main` at `8df26973fce788cac29cc8d8ab925781ee2ef63e` and
`djconnect-windows` `main` at `b1947ca3f7952a8e947561ac27c6c8d80ba0404d`.
This assessment adds no Runtime, Apple, Windows, API, roadmap or Execution
Horizon behavior.

## Canonical boundary

Apple and Windows are personal, registered rich Renderer Hosts. Home Assistant
remains the owner of Profile resolution, Session Runtime, Planner, immutable
DJMoments, Session Flow, Presentation, Broadcast, Ask DJ interpretation,
Discovery and Music Backend behavior. Both clients render returned personal or
renderer-safe state and submit only existing authorized commands.

Capability parity is not a goal. Canonical renderer behavior is the goal:
where a server-owned renderer projection is selected for both rich clients, it
must retain its owner and contract. Platform-native presentation is
platform-only unless the canonical architecture explicitly promotes it.

## Repository evidence

| Evidence source | Observed evidence |
| --- | --- |
| Platform foundation | The Capability Model and Renderer Experience Roadmap identify personal Apple and Windows rich-client access to Playback, Ask DJ, Track Insight and Discover; Session Flow is a renderer-safe HA-owned projection. |
| Apple Renderer Host | Native session runtime models and iOS Active DJ Session surface render active Session state, planner direction and Session Flow. Apple also has native Ask DJ text/PTT, Track Insight, Discover, Watch, widgets, Live Activity and Track Insight ShareLink evidence. |
| Windows Renderer Host | Native MAUI source renders Now Playing, bounded controls, queue/playlists, Ask DJ text/history/actions, Track Insight and Discover. It has profile/session request context but no current Session Flow, Session Direction, Session Projection or Current DJMoment model/surface. |

## Capability matrix

| Canonical renderer capability | Apple | Windows | Convergence disposition |
| --- | --- | --- | --- |
| Personal registered renderer identity and backend-resolved Profile context | Supported | Supported | Shared |
| Current playback, artwork and bounded controls | Supported | Supported | Shared |
| Backend-authorized queue and playlists | Supported | Supported | Shared |
| Ask DJ text, revisioned history and server-returned actions | Supported | Supported | Shared |
| Ask DJ push-to-talk / voice input | Supported | Absent | No canonical parity requirement is recorded; Apple native voice remains platform-specific evidence. |
| Discover / Music Discovery, backend reasons and Play Now | Supported | Supported | Shared |
| Renderer-safe Track Insight | Supported | Supported | Shared |
| Native Track Insight sharing | Supported | Absent | Intentional Difference: Apple is the sole CMB-11 reference native-share Renderer Host. |
| Active Session state and Session Flow | Supported | Absent | Future Convergence: the canonical renderer roadmap identifies Session Flow for Apple and Windows rich clients, but current Windows source has no corresponding model or surface. |
| Session Direction / Session Projection | Supported for active Session direction | Absent | Future Convergence: Windows has request-context `session_id`, not an active renderer projection. |
| Explicit Current DJMoment renderer surface | Absent | Absent | Future Convergence only after a separate renderer contract decision; neither repository establishes a dedicated current-Moment surface. |
| Interactive DJMoments | Absent | Absent | Future assessment: both personal Renderer Hosts are eligible presentation candidates, but no capability is implemented or selected. |
| Session Continuation | Absent | Absent | Future assessment: both may be continuation renderers only after the independently registered capability assessment; neither owns delivery or Session continuation. |
| Apple Watch, widgets, Live Activity and Share Sheet | Supported | Absent | Intentional Difference / platform-only; renderer parity is not required. |
| Windows Jump Lists, Windows notifications and other native Windows surfaces | Absent | Absent | Platform-only and unselected; their absence does not create Apple parity work. |

## Ownership and experience result

The shared personal-renderer contract is qualified for Profile context,
Playback, queue/playlists, Ask DJ text/history/actions, Discover and Track
Insight. Apple and Windows preserve the same Home Assistant ownership boundary;
neither gains local Session, Planner, Knowledge, DJMoment, Broadcast or Music
Backend authority.

Apple's ShareLink, Watch, widgets and Live Activity are local native
realizations, not shared renderer requirements. Conversely, no Windows-native
surface is inferred from Apple evidence. The two platforms may intentionally
present the same server projection differently.

Apple's active Session surface supplies source evidence for Session Flow and
Direction. Windows source presently contains only `session_id` request context,
without the active Session projection models or presentation. This is an
objective convergence qualification gap, not a claim that Windows is behind or
an implementation authorization. Neither source establishes a dedicated
Current DJMoment renderer surface, so it remains a future contract question
rather than a platform discrepancy.

## Remaining qualification items

1. **Rich-renderer active-Session contract disposition** — use current
   Apple/Windows and canonical renderer evidence to decide whether the
   renderer-safe active Session Flow, Direction and Current DJMoment
   projections are shared rich-renderer requirements, retained platform
   divergence or separately selected capabilities. No implementation follows
   from this item.

The item is a Future Assessment under Platform Evolution. It does not change
the Execution Horizon or authorize Apple or Windows work.

## Sources

- [DJConnect Capability Model](../../DJCONNECT_CAPABILITY_MODEL.md)
- [Renderer Experience Roadmap](RENDERER_EXPERIENCE_ROADMAP.md)
- [Renderer Host Classification](../technical/RENDERER_HOST_CLASSIFICATION.md)
- [Product Roadmap](../../PRODUCT_ROADMAP.md)
- `djconnect-app` `Sources/DJConnectCore/DJConnectSessionRuntime.swift` and
  `Sources/DJConnectUI/DJConnectRootView.swift`
- `djconnect-windows` `docs/ARCHITECTURE.md`,
  `src/DJConnect.Windows/MainPage.xaml` and
  `src/DJConnect.Windows/Models/ApiModels.cs`
