# CMB-05 — Raspberry Pi 4-inch Capability Profile Assessment

**Status:** Assessment complete

**Decision:** `GO_PI_4_INCH_PROFILE_PARTIALLY_QUALIFIED`

**Scope:** Repository-first comparison of the canonical DJConnect architecture
with `djconnect-pi` current `main` at `45be2233b33faa31b4dadc9ceba52a8d1ec5c2e0`.
No Pi, Runtime, Renderer, Browser Receiver, Universal Receiver, API or roadmap
behavior changes.

## Canonical role

The Pi 4-inch is a **Registered + Interactive Shared Appliance Host**: a
compact, continuous-presence shared-room controller and native Renderer Host.
It exists to expose bounded playback, current playback and a compact,
renderer-safe Current DJMoment, not to become a personal rich client, Session
owner or universal wall display. Home Assistant retains the Runtime, Planner,
Knowledge, Conversation, Music Backend, authorization and canonical
projections.

Its secondary role is a local appliance Interaction Host for simple,
authorized playback and backend-supported queue/playlist actions. It does not
coordinate a Session, infer identity, create DJ intelligence, own a Playback
Runtime or replace a personal Apple/Windows client.

## Capability profile

| Dimension | Canonical Pi 4-inch profile | Current Pi-repository evidence | Qualification |
| --- | --- | --- | --- |
| Renderer role | Compact shared-room, Registered + Interactive native appliance. | 720×720 fullscreen QML touch remote for Pi Zero 2 W / HyperPixel 4.0-style hardware; local-only pairing, kiosk lifecycle and appliance diagnostics. | Qualified. |
| Playback | Current track, artwork, artist, status, compact progress, bounded controls, volume/output, queue and playlists where the backend permits. | Now Playing, dedicated control surface, artwork, queue, playlists, output, shuffle/repeat and bounded command set are present. | Qualified. |
| Interaction | Play, pause, next, previous, volume, output and backend-authorized queue/playlist selection. | Those commands are present; the display intentionally caps playback-volume presentation and retains appliance settings. | Qualified. |
| DJ projection | Compact Current DJMoment and renderer-safe Track Insight. | Track Insight is rendered from HA response data; the architecture permits compact Current DJMoment. | Partially qualified: current repository evidence does not establish the deployed 4-inch Current DJMoment surface on target hardware. |
| Session Flow | Intentionally absent. A full Flow/timeline belongs to Pi 10-inch and eligible rich/Universal Receiver surfaces. | No canonical 4-inch Session Flow surface is established by the reviewed QML/README evidence. | Qualified intentional absence. |
| Ask DJ | Bounded read-only structured actions only; no free prompt, PTT, local TTS or local audio. | Read-only history/action UI, server-side clear and no local prompt input/PTT/TTS/audio are documented. | Qualified at contract level. |
| Privacy | Shared/household-first; no locally inferred personal identity, personal history or personal Music DNA on a shared surface without explicit backend profile resolution. | The client documents profile isolation, but also exposes Music DNA, Discover and conversation-history screens when a backend resolves a personal profile. | Partially qualified: the shared-surface visibility boundary requires explicit profile-surface evidence. |
| Technology | Native QML is canonical normal operation; Pi is not a Universal Receiver. | PySide6/Qt Quick/QML native client and local appliance API are current. | Qualified. |

## Hardware and technology boundary

The 4-inch, 720×720 touch display and Pi Zero 2 W appliance context favor a
single compact current-state view, explicit large controls, bounded artwork
caching and continuous local presence. They do not establish a rich timeline or
personal dashboard requirement. Native QML remains canonical; the browser-based
Universal Receiver is an independent Home Assistant-hosted Renderer Host and
may not replace the Pi appliance architecture.

Pi 4-inch is not a reduced Pi 10-inch. Pi 10-inch receives its own assessment
and may expose renderer-safe Session Flow and Presentation projections. No
capability inheritance or parity follows between the two hosts.

## Observed intentional differences

The following are deliberate profile differences, not deficits or future
implementation commitments:

- full Session Flow and Presentation timeline absence;
- no local Runtime, Planner, Knowledge, Music Backend or Session authority;
- no local voice capture, PTT, TTS or DJ-response audio;
- no locally inferred personal identity or locally authoritative Music DNA;
- native QML appliance realization instead of Universal Receiver/browser
  realization.

## Remaining qualification items

1. **Target-hardware compact DJ projection evidence** — confirm the Current
   DJMoment surface and the bounded playback/QML profile on the actual 4-inch
   appliance; current evidence establishes the contract and source UI but not
   the deployed target-hardware result.
2. **Shared-profile visibility evidence** — reconcile the existing rich
   Music DNA, Discover and conversation-history surfaces with the canonical
   shared-appliance privacy boundary, using only backend-resolved profile and
   surface-visibility evidence.

Both items are Future Assessment evidence. They authorize no Pi code, UI
change, privacy-policy change or profile-feature removal.
