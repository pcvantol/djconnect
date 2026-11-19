# Profile-authorized native Pi app — owner scope clarification

Owner-selected scope, recorded and explicitly expanded on 20 October 2026. Core owns this capability
clarification; the existing Pi writer owns implementation in
`pcvantol/djconnect-pi` PR111. This local source increment is not a protected
consumer pin, implementation qualification, installation or physical acceptance.

## Selected product scope

The owner selected one complete native app for Pi10 and the four-inch Pi,
explicitly linked to an authorized Profile on each device, with **the same
feature set as the Apple application**. This includes Session and Flow,
Now Playing and remote music controls, queue, playlists and albums, Ask DJ text,
selected-contribution “tell me more”, relevant follow-ups, history, Music DNA,
Discover, shared settings, rich media and other authorized app interactions.
Feature delivery and any common producer gaps remain separately qualified.
Neither a small screen nor `client_type: raspberry_pi` is a reason to prohibit
these shared features. Native layout adapts to display size and device resources.

This replaces the earlier shared-appliance-only/no-Flow/no-free-prompt product
dispositions for the Profile-authorized app on **both** sizes. The original
CMB-05/CMB-06 assessments remain immutable historical evidence, linked from the
updated current capability documents. Their completed old assessments do not
establish delivery of the current complete app.

## Existing authority and transport

The client remains `client_type: raspberry_pi`, with the existing matching
device identity, pairing credentials and server-resolved authorized Profile.
It does not infer personal identity from room, screen size, cached UI or another
device. Unpaired/not-configured devices do not receive a synthetic Profile.

Text uses the existing paired `POST /api/djconnect/v1/ask_dj/message` service.
The [common conversation contract](ASK_DJ_CONTEXTUAL_DIALOGUE_CONTRACT_V1.md)
and [Profile/Session history contract](SESSION_CONVERSATION_HISTORY_CONTRACT.md)
retain owner, source, clear, revision, expiry and replay guards. An optional
current Session enriches that common route; standalone `session_id: null`
does not create another conversation owner. Selected old entries remain
references and never authorize writes into an old archive.

The server remains the owner of Session lifecycle, DJ intelligence, narrative
content, Mood, Music DNA opt-in, history and playback effects. The client shows
only actually granted functions and performs only explicit permitted actions.
This document invents no new capability JSON field or endpoint. A client-local
free-input declaration is not a server permission or an independent producer pin.

## Hardware detection and client/server handshake

Current target Pi hardware has no available speech input or local audio playback.
That limits available routes, not the shared product contract. The client detects
microphone/capture, speech-provider and local audio-output support, including OS
permission, and negotiates supported functions with the server through the
common capability handshake. Do not implement a blanket Pi/client-type ban or
invent a separate Pi voice/conversation contract. This scope clarification does
not invent new wire fields or claim the handshake is already implemented.

Offer a route only when the actual client capability, relevant server capability,
current authorization and explicit user choice permit it. Unknown, missing,
denied or withdrawn support is unavailable. Hide unavailable microphone/PTT,
local speech and local audio-playback actions; retain text-only operation and
all other permitted app features. Re-evaluate on reconnect and capability,
permission or output changes; stale capability cache must not keep a route active.
A future capable Pi does not need a product-scope amendment solely because it
can supply a microphone or speaker; its concrete route still needs implementation
and ordinary qualification.

Remote Spotify/HA playback remains available on authorized outputs. A Pi without
a local speaker can still control play/pause, queue, playlists/albums, volume and
output selection. “No local playback” must not hide those remote music controls.
Likewise, a missing local speech route alone is not proof that a separately
available, authorized HA route is unavailable; present actual target/route
availability using the common speech policy and its text-only preference.

## Private app versus shared display

Profile authorization is required for each surface. A shared/guest/VibeCast
projection remains bounded to its own admitted data; this app selection does
not publish personal Ask DJ history, DNA or Profile details to a wall, guest,
broadcast, notification or other device. Registered + Interactive host
classification is not permission to expose private content.

The client must withdraw stale content on lost authorization/Profile, clear,
source withdrawal, applicable expiry or owner/session-generation change.
Historical content uses the existing representation, retained-until and current
rights; transient actions/media do not inherit the text's retention grant.

## Standalone private-answer lifetime is a remaining producer gap

Protected Core `8b221d07fe2215d9516d18fe92c832332c7a16ab` can return
`conversation.history_scope: private_ephemeral` with no persisted exchange.
Its general standalone response does not provide a dedicated original UI
`display_expires_at` for that answer. The 20-minute `DialogueState` idle eviction
is internal RAM management and its touched time can change. It is not a
nonrenewable client display deadline. Native Moment/Silence display leases
and speech deadlines belong to their own admitted objects and are not a
substitute for an Ask DJ bubble's contract.

No consumer may claim that missing producer field was supplied, infer a
qualified UI lease from the RAM window, or use a local timer as release evidence.
A concrete server-owned lifetime contract and its qualification remain OPEN.
This readback answers the protected-main question without fabricating a new
deadline, refreshing source rights or declaring private UI acceptance.

## Remaining acceptance

The Pi writer must qualify decode, owner/revision/lifecycle handling, native
layout and continuity on both sizes, then follow its protected delivery and
separate installation gates. Local QML/unit/render fixtures, a source merge,
screenshots and an unpaired Pi are not proof of a working live chain.
Core consumer pins and any missing producer contracts must be independently
admitted before activation; this clarification alone activates nothing.
