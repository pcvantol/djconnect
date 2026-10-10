# Shared VibeCast renderer and versioned host builds

## Additive Cast status candidate

Build 1.1.0 adds the opt-in [Cast status v1 contract](VIBECAST_CAST_STATUS_CONTRACT.md).
Core alone maintains namespace/readiness handling and lifecycle feedback. Both
hosts retain the existing renderer behavior; legacy v1 handoffs receive no new
status messages. New senders correlate directed statuses and expire missing
presentation leases. The published 1.0.0 pin below remains historical; no
receiver promotion or installed/hardware claim follows from the new candidate.

## Source delivery receipt

Protected PR#1136 source-main b211e5e99235e5862b3befb100dd9e64438f6e80 equals reviewed
7460ef5e1d4c15888569b857d7c636620ace7e37. Static build1.0.0's supplying revision
is that exact reviewed commit; runtime/software source bytes also equal main.
ManifestSHA25672239b476e793fe5bb5493d2be5720fcd1f6e64ea83e012c77573732a58c7898;
bundleSHA256dfb800634652de610e6d3861bc0aedfa1e1cdb1a65dc80b3bdd4a2a3326c56d1.
Pinned import must validate the external manifest digest and exact revision
with --verify-existing; unpinned verify() is structural/asset validation, not
manifest authenticity. The protected source/internal bundle approval grants
no Pages/receiverpush/install/hardware authority. Source completion and
Finalization are recorded in [the delivery report](../history/prompts/2026-10-09-vibecast-shared-renderer-finalization.md).

Assignment: `DJC-CORE-VIBECAST-SHARED-RENDERER-V1-20261009`.
Owner decisions: Core #1101/6078489341 and VibeCast #10/6063499443.

Core owns one source in `custom_components/djconnect/vibecast_renderer`.
`template.html`, `style.css` and `renderer.js` are migrated from the existing
rich `vibecast.html`. Common presentation and transport ordering/expiry remain
one implementation; `local-host.js` supplies the existing browser claim, while
`cast-host.js` supplies only CAF v1 handoff. No host performs Knowledge, Planner,
Persona realization, Moment production, history search or backend playback.

`python3 scripts/build_vibecast.py --output <directory> --write-local` regenerates
the committed, self-contained integration entry. `--check-local` rejects drift.
The same deterministic build produces `local/vibecast.html`, `cast/index.html`
and `manifest.json`. Generated entries are distribution products; edit only the
source modules. Every required source and output has a SHA256, plus build
version, exact supplying commit, supported contracts and capability requirements.
A build has no timestamp, machine paths, HA address, token or Session content.
Repeat the build with the same supplying commit and compare every output byte.
`verify()` rejects missing, changed and unexpected assets. The normal test suite
checks committed local-output equivalence, keeping the existing CI entrypoints.

The Pi/browser continues to load its own HA `/djconnect/vibecast`. All CSS and
scripts are in the integration entry; no CDN, Pages or CAF dependency. HA serves
HTML with its existing no-store/no-referrer headers. The static Cast entry loads
CAF and uses `addCustomMessageListener` with existing namespace
`urn:x-cast:com.djconnect.vibecast.v1`. A hidden media element meets CAF's context
requirement; no media URL, music or DJ audio is loaded. This is a visual receiver.

## Temporary receiver authority and compatibility

The existing v1 message is `kind: vibecast_handoff`, `version: 1`, `ha_url`
(exact HTTPS origin), `session_id`, `broadcast_token`, optional locale. No
credentials/instance/Session are accepted from the static page URL. Non-HTTPS,
userinfo, paths, queries/fragments, malformed identities and unsupported message
versions fail closed with localized copy. The adapter forwards only the existing
read-only Session authority. A sender-provided end_grant is ignored; the existing
local opt-in server-issued end-grant remains independently scoped.

The common renderer connects directly to that HA Broadcast WebSocket, resolves
relative artwork against HA, and accepts snapshot/event v1. Static snapshots
require matching Session identity, view_broadcast true and owner_controls false;
unknown explicit schema versions are rejected. Optional artwork, next item and
attribution remain optional. This qualifies the actual current producer, not an
arbitrary historic HA-version range or every future schema.

Browser WebSockets do not enforce ordinary HTTP CORS. The existing server route
therefore allows its own exact origin or an exact HTTPS origin from HA's existing
`http.cors_allowed_origins` configuration. Wildcard/null origins grant nothing.
Missing Origin retains existing non-browser clients. There is no new endpoint,
proxy, receiver directory, credentialed wildcard CORS or custom settings store.
A deployowner must arrange valid HA HTTPS, DNS/routing and its exact receiver
origin in HA's allowlist. An HTTPS Pages app cannot silently downgrade to local
HTTP, bypass certificates or rely on the sender as a data relay.

Common ordering, dedupe, track binding and bounded card expiry apply to both
hosts. Host stop clears local projections, timers and credentials; it does not
end the Session. New handoffs invalidate the old socket and sequence context.
Runtime-end and token rejection remove current content. Reconnect cannot revive
expired cards. A delayed explicit local end response cannot end a newly handed
off Session in the renderer. No personal questions/answers, archives, search or
Profile surface is introduced; Apple owner endpoints remain separately owned.

## webOS compatibility boundary

LG's [official engine table](https://webostv.developer.lge.com/develop/specifications/web-api-and-web-engine)
identifies 2020/webOS5.x as Chromium68. Shared source avoids optional chaining,
Array.at and replaceAll; layout supplies vh/pixel/color fallbacks before modern
clamp/min/dvh/color-mix and glass effects. Host adapters are independent: ordinary
browsers never require CAF. A later LG host can supply the same temporary handoff
and host-stop boundary without another bubble implementation. Current browser
proof is not a Chromium68 emulator or physical CX result. Actual sdkVersion,
firmware, viewport, input/suspend and .ipk qualification remain LG-owner work.

CAF's [official context API](https://developers.google.com/cast/docs/reference/web_receiver/cast.framework.CastReceiverContext)
is the reference for custom-message registration. A modeled CAF listener test
qualifies our adapter contract only, not the real Google SDK or Cast hardware.

## Distribution and evidence boundary

Receiver repository `pcvantol/djconnect-vibecast-receiver` owns reviewed import,
Pages deployment, public fixed receiver URL and Cast registration. Import the
pinned static entry and manifest with checksum verification; never independently
edit generated bubbles. Promote/roll back static code by immutable source/build
identity, independently of runtime Session data. Core merge does not promote
Pages. Source/internal prerelease and Finalization publications each require
specific approval. No receiver push, Pages deployment, tv installation or
hardware PASS follows from this build. Pi capture/frame-rate remains PARTIAL.

Software proof uses an isolated real HA2026.10 router and Runtime/Broadcast with
synthetic qualified MusicBrainz evidence. Local browser claim and actual TLS
WebSockets are exercised; only CAF message transport is modeled. The test CA is
trusted inside the disposable container's NSS profile, never on the maintainer
Mac. No ignoreHTTPSErrors, insecure-cert flags, auth bypass, live provider or
HA-dev configuration is used. Before/after images, movement recordings and exact
source/build receipts distinguish software, distribution and hardware gates.
