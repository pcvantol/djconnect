# Raspberry Pi 10-inch — current application capability profile

**Current product decision:** Apple feature parity for the Profile-authorized
native Pi app, explicitly confirmed by the owner on 20 October 2026.
**Implementation and acceptance:** separately qualified, not established by this document.

The 10-inch device runs the same native Pi application and exposes the same
server-owned feature set as the Apple application. Screen size changes layout,
navigation density and performance budgets; it does not remove Session Flow,
free-text Ask DJ, Music DNA, history, Discover, rich contributions or authorized
interaction. Use the [shared Pi app scope](PI_PROFILE_AUTHORIZED_APP_V1.md) for
the complete capability, pairing and hardware-handshake rules.

## Authorization and runtime ownership

Each device must be explicitly linked to its server-authorized Profile.
The same owner, Profile, Session, source, revision, expiry and action permissions
apply as on Apple. Shared/guest/VibeCast presentation remains a separately
restricted surface; mounting the device on a wall does not itself turn a
Profile-authorized private app into a guest renderer.

Home Assistant owns Session lifecycle, intelligence, history, knowledge,
recommendations and playback effects. The Pi presents the existing shared
contracts through native QML/PySide6 and sends explicit permitted commands;
it does not create a local planner or a separate Pi conversation contract.

## Hardware availability

The selected hardware currently has no available speech input or local audio
playback. Hide unavailable microphone, PTT, speech and local playback controls.
This is a detected client/device capability, not a permanent Raspberry Pi API
or product prohibition. A capable, permission-granted device may negotiate
those routes through the common client/server handshake when implemented and
qualified. Missing or unknown support means unavailable; model, screen size or
`client_type` alone is not evidence of audio hardware.

Spotify/HA playback on another authorized output remains controllable, including
queue, playlists, albums, volume and output selection. Lack of a local speaker
does not disable those remote music controls.

## Qualification still required

Qualify the actual 10-inch native layout, lifecycle, owner/Profile isolation,
common feature behavior and handshake/route withdrawal on the target device.
An unsupported hardware route must remain hidden without blocking text or the
rest of the application. Source/unit/render evidence, installation, live server
behavior and physical or audible acceptance are separate outcomes.

The previous CMB-06 assessment concerned a much narrower shared-appliance
implementation at a pinned old source. Its [immutable assessment record](../history/assessments/CMB_06_PI_10_INCH_20261020_SUPERSEDED.md)
retains that evidence, including its old qualification decision. Its intentional
feature omissions are superseded product scope and are not current Pi restrictions.
