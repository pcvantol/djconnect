# Raspberry Pi Application and Renderer Family

**Status:** Current canonical reference; owner clarification20October2026.

Both supported display sizes use one complete native QML/PySide6 application
with the same Profile-authorized feature set as Apple. The family includes
Interaction and Renderer roles but remains a client of Home Assistant's shared
services. It never owns Session Runtime, Planner, Knowledge, Conversation,
Profile, Music DNA or canonical history.

## Current capability comparison

| Capability | Pi4-inch | Pi10-inch |
| --- | --- | --- |
| Profile | Explicit authorized binding per device | Explicit authorized binding per device |
| Session and Flow | Same target app features as Apple | Same target app features as Apple |
| Ask DJ | Free-text, selected-contribution more, follow-ups and rich answers | Same common features |
| History, Music DNA and Discover | Same authorized app functions | Same authorized app functions |
| Settings and rich interactions | Common server-owned features and action permissions | Same common features |
| Remote music controls | Authorized Spotify/HA outputs, queue, albums/playlists, volume and output selection | Same common features |
| Speech input and local audio | Unavailable on current hardware; detect and negotiate availability | Unavailable on current hardware; detect and negotiate availability |
| Presentation | Compact adaptive native layout | Larger adaptive native layout |

These are product targets, not implementation or acceptance results. A common
feature missing a producer or consumer still needs its ordinary implementation
and qualification. No permanent no-Flow, read-only Ask DJ, no-history or
no-personal-dashboard rule applies solely because the client is a Raspberry Pi.
Native OS integrations retain their concrete platform realization; parity does
not claim an Apple OS service exists on Linux.

## Hardware, authorization and presentation

The [current app scope](PI_PROFILE_AUTHORIZED_APP_V1.md) specifies capability
handshake and hardware handling. Unknown/missing/withdrawn speech or local output
support hides only the unavailable route. A local speaker is not needed to
control a remote music output. The server remains authoritative for authorization,
Session, Profile, content, history and effects.

A shared/guest/wall projection is separately admitted and privacy-bounded. Wall
mounting or permanent power does not convert an explicitly Profile-authorized
app into a guest surface or grant private data to a broadcast. Native QML remains
normal operation; Universal Receiver/VibeCast remain independent browser products.
Pi-local deployment/update/lifecycle/watchdog/diagnostics are shared platform
concerns; screen size and resources determine presentation and device validation.

## References and historical evidence

- [Raspberry Pi Platform Foundation](../../RASPBERRY_PI_PLATFORM_FOUNDATION.md)
- [Current Pi4-inch profile](PI_4_INCH_CAPABILITY_PROFILE_ASSESSMENT.md)
- [Current Pi10-inch profile](PI_10_INCH_CAPABILITY_PROFILE_ASSESSMENT.md)
- [Renderer Host Classification](../technical/RENDERER_HOST_CLASSIFICATION.md)
- [Prior restricted family reference](../history/assessments/PI_RENDERER_FAMILY_20261020_SUPERSEDED.md)

Historical qualification remains attached to its original source and scope.
It is not installed/native/physical acceptance of the complete current app.
