# CMB-06 — Raspberry Pi 10-inch Capability Profile Assessment

**Status:** Assessment complete

**Decision:** `GO_PI_10_INCH_PROFILE_PARTIALLY_QUALIFIED`

**Scope:** Repository-first architecture assessment with `djconnect-pi` current
`main` at `45be2233b33faa31b4dadc9ceba52a8d1ec5c2e0` as implementation evidence.
The Pi repository contains shared native QML/PySide6 appliance infrastructure,
but no separate Pi 10-inch renderer implementation. That absence is expected.
No Pi code, Runtime, Renderer, Browser Receiver, Universal Receiver, API,
roadmap or Execution Horizon behavior changes.

## Canonical profile

Pi 10-inch is a **Registered + Interactive Shared Appliance Host** and the
dedicated, always-on household wall experience. Its primary role is an
authorized visual active-Session surface; its secondary role is bounded,
explicit playback interaction. It does not own a Session, Runtime, Planner,
Knowledge, DJMoment, Broadcast, authorization decision or Music Backend.

The canonical active-Session surface is:

| Capability | Pi 10-inch disposition |
| --- | --- |
| Current playback | Renderer-safe artwork, track, artist, status, progress and bounded output/control projection. |
| Current DJMoment | Renderer-safe current immutable DJMoment and resolved Presentation. |
| Session experience | Full active renderer-safe Session Flow and Presentation timeline, owned by HA and presented without local ordering authority. |
| Session context | Compact renderer-safe Session Direction / active DJ context where supplied by an existing authorized projection. |
| Playback interaction | Explicit play, pause, next, previous, volume/output and backend-authorized queue/playlist actions. |
| Ask DJ | At most renderer-safe, explicitly authorized shared-surface projection or actions; no unrestricted personal history, free-form shared chat authority, local PTT, TTS or local DJ audio. |

The full Session Flow is canonical for Pi 10-inch and intentionally absent on
Pi 4-inch. The two hosts are independently assessed: Pi 10-inch is not an
expanded Pi 4-inch, and Pi 4-inch is not a reduced Pi 10-inch.

## Experience, interaction and privacy boundaries

The 10.1-inch portrait, touch, permanent wall-mount and continuous appliance
context support glanceable shared Session presentation and explicit nearby
touch interaction. They do not establish a personal dashboard, second music
player, Browser Receiver, local Session continuity mechanism or renderer-owned
social/audience authority.

Interactive DJMoments are not a current Pi 10-inch capability. A future
assessment may determine whether existing renderer-safe, bounded response
forms suit the shared wall surface; it may not infer Quiz, Poll, Prediction or
Audience Expression delivery from this profile. Audience Experience remains
deferred and server-owned; no participant identity, free-form chat, personal
history, audience control or Planner influence belongs to this host.

Music DNA, Profile details, personal Ask DJ history, provider payloads,
credentials, tokens, internal Runtime context and private Session history must
never appear on the shared wall surface. A backend-resolved shared profile may
provide only the existing renderer-safe shared projection; the Pi never infers
a personal identity locally.

## Native technology boundary

Native QML remains the canonical Pi 10-inch implementation direction. The
existing Pi repository supplies native QML/PySide6, kiosk/appliance lifecycle,
deployment, update and diagnostics foundations. Universal Receiver remains a
separate HA-hosted browser Renderer Host and cannot replace the Pi native
appliance. A kiosk browser is therefore not the canonical Pi 10-inch profile.

## Qualification result

The capability profile is sufficient to bound later implementation, but is
only partially qualified because no repository evidence yet identifies and
qualifies the concrete 10.1-inch portrait display, touch/mount/deployment path
or its native appliance behavior on target hardware.

### Remaining qualification items

1. **Concrete 10-inch hardware and appliance evidence** — identify the target
   portrait display/touch/mount and qualify native QML deployment, continuous
   presence and shared-room operation on that hardware.
2. **Shared-wall projection evidence** — qualify the existing renderer-safe
   Session Flow, Presentation and bounded shared-profile visibility on the
   concrete host before implementation validation.

Both are Future Assessment evidence. They authorize no Pi implementation,
browser substitution, Audience capability, Interactive DJMoment capability,
privacy-policy change or API expansion.
