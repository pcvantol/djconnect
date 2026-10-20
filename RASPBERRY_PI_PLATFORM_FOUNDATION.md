# Raspberry Pi Platform Foundation v3

**Status:** Canonical Platform Foundation; owner scope corrected20October2026.
**Owner:** DJConnect Platform Foundation.

## Product scope

Pi4-inch and Pi10-inch run one complete native application with the same
feature set as Apple. Each app explicitly links to its authorized Profile.
The [shared app scope](docs/product/PI_PROFILE_AUTHORIZED_APP_V1.md) is the current
capability reference. A smaller display changes layout and performance budgets,
not access to Session Flow, free-text Ask DJ, history, Music DNA, Discover,
settings, rich contributions or authorized interactions and remote music controls.
The previous intentional rich-feature omissions are superseded product decisions.

| Concrete host | Implementation | Target feature set | Device-specific qualification |
| --- | --- | --- | --- |
| Pi4-inch | Native QML/PySide6 application | Same Profile-authorized app features as Apple and Pi10-inch | Compact layout, touch, resources and actual hardware capabilities. |
| Pi10-inch | Same native QML/PySide6 application | Same Profile-authorized app features as Apple and Pi4-inch | Larger layout, touch, resources and actual hardware capabilities. |

Shared source or product parity does not prove that either device is implemented,
installed or qualified. Existing server/consumer gaps remain objective remaining
work, not a justification for a permanent Pi-specific feature prohibition.

## Common server ownership

The family consumes the [Capability Model](DJCONNECT_CAPABILITY_MODEL.md) and
[Host Role Architecture](HOST_ROLE_ARCHITECTURE.md). Home Assistant remains the
only Session Runtime, Planner, Knowledge, Conversation and Music Backend owner.
There is no Pi-owned conversation, intelligence, Profile or history authority.
The Pi uses existing shared app routes and only server-authorized actions.

Native QML is the normal Pi application implementation. The Universal Receiver
remains an independent browser Renderer Host; it does not replace the native app.
Pi-local bootstrap, updates, display/power policy, watchdog and diagnostics remain
platform concerns, separate from canonical Session state.

## Hardware and route availability

Current Pi targets have no available speech input or local audio playback. The
client detects hardware/provider support and OS permissions and negotiates
availability with the server through the common capability handshake. Missing,
unknown, denied or withdrawn support is unavailable; hide its controls and keep
text and the rest of the application available. Do not infer availability or a
permanent prohibition from `client_type`, screen size or device name.

Remote Spotify/HA playback is independent of a local speaker. Authorized
play/pause, queue, album/playlist, volume and output controls remain available.
A capable future device can negotiate the common speech/audio route without a
new Pi product-scope exception; implementation and route qualification are still
required. This document does not invent a wire field, configure a provider,
change permissions or activate an unimplemented route.

## Profile application versus shared projection

The explicitly Profile-authorized app may expose the same permitted personal
features as Apple. A wall mount is not an authorization mode. Registration alone
does not identify a person; each device must obtain its explicit Profile binding.
A separately admitted shared/guest/ambient/VibeCast surface receives only its
own safe projection and must not inherit private history, Music DNA or Profile
details from the native app. Offline cache cannot become server truth.

Session/owner/source/revision/retention/clear/expiry and reconnect withdrawal
remain the common server contracts. Ambient/sleep transitions are presentation
or device-power behavior; they neither create a Session nor widen authorization.

## Evidence and history

The [4-inch](docs/product/PI_4_INCH_CAPABILITY_PROFILE_ASSESSMENT.md) and
[10-inch](docs/product/PI_10_INCH_CAPABILITY_PROFILE_ASSESSMENT.md) current profiles
use this scope. Native decode/render, live server behavior, installation and
physical/audio outcomes must each be qualified on the actual target.
Historical CMB05/06 qualification does not qualify this complete application.

The exact [previous foundation](docs/history/assessments/PI_PLATFORM_FOUNDATION_V2_20261020_SUPERSEDED.md)
and [previous family reference](docs/history/assessments/PI_RENDERER_FAMILY_20261020_SUPERSEDED.md)
are retained as historical evidence, not current capability restrictions.
