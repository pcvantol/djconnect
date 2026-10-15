# VibeCast web entry, distribution and optional Cast v1

Status: selected **documentary decision delta**, not runtime/CI/deployment proof.
Authority: [DJC-VIBECAST-WEB-FIRST-DECISIONS-DELTA-V1-20261015](https://github.com/pcvantol/djconnect/issues/1174#issuecomment-6201605985).
Parent: [experience](VIBECAST_WEB_FIRST_EXPERIENCE_V1.md),
[trust](VIBECAST_ONBOARDING_GUEST_AUTHORITY_V1.md),
[Apple mode](APPLE_VIBECAST_GUEST_MODE_V1.md).
New decisions follow source1175/Finalization1176; their evidence stays immutable.

## Resolved decisions, genuine remaining choices

**RESOLVED:** `https://vibecast.tv/` root is the direct central QR/start entry.
Peter reports domain purchase through Cloudflare. DNS/zone/account/TLS/Pages and
live onboarding are unverified by that statement. No mandatory path or marketing
interstitial. Public alias is not protocol identity.

**RESOLVED:** the web-first exception is joining in the existing DJConnect app.
Unpaired pairing screen offers discovery and guest QR without completing pairing;
paired main view offers independent guest QR and, after contextual permission,
opportunistic discovery with a calm highlighted top menu item. No blinking,
automatic join/navigation or credential transfer. Multiple sessions require
explicit choice. HA/local server advertises; a TV webpage does not. No tokens,
private Profile fields or physical-presence assurance in mDNS.

**PARTIAL PREFERENCE, NOT FINAL REACTION SELECTION:** 🤩 replaces 🤯 in the
working ❤️/🔥/😌/🤩/👎 proposal. 🚀 is open as an extra or alternative. Final
set/count/labels remain open; it blocks neither web bootstrap nor CI. Reactions
remain ephemeral subject-bound advisory signals, never direct Mood/skip,
preferences/history or Music DNA. Existing [Audience](AUDIENCE_EXPERIENCE_ARCHITECTURE.md)
meaning/authority boundaries remain.

Other genuine implementation decisions: reviewed rendezvous wire/crypto and
original TTL/budgets, actual service/account binding, safe browser minimum and
bug exceptions, Apple isolated WebView versus native rendering, shared imagery/
speech rights, share/cancel policy and qualified Cast continuity under real CAF.
There is no reopened domain or unspecified-exception choice.

## Repository and CI ownership

| Owner | Source and delivery responsibility | Excluded authority |
| --- | --- | --- |
| djconnect-vibecast-receiver | Central vibecast.tv UI, own tests/build/CI/CD and static distribution, separate bootstrap entry/output/Pages target beside existing Cast output | No rendezvous Worker/D1/service, Session/user backend, owner credentials or analytics |
| djconnect Core | One `custom_components/djconnect/vibecast_renderer` source, HA display/guest pages, grants/media/Session/AskDJ/Planner/playback owners | No second receiver-local intelligence or hand-maintained renderer copy |
| djconnect-api | Proposed bounded temporary rendezvous service, own Worker/security/deployment and reviewed wire binding | No APNs keys/registration-data reuse or general central Session engine |
| djconnect-website | Marketing, explanation and links to root entry | No second runtime or token store |
| djconnect-app | Paired owner display scanner; both guest entries, isolated temporary shell and safe home return | No central relay or inferred guest/owner capability |

No new repo or source move. Receiver implementation must explicitly widen its
currently Cast-only README/AGENTS/development extension to bootstrap plus static
receiver distribution, with generated governance kept consistent through its
normal materializer/validator. Core keeps the renderer; receiver imports Cast
artifacts by exact source revision/manifest/hash. Never hand-edit generated
`wwwroot/index.html`, vendor, locks or one-off copies of rich renderer code.

Preferred delivery design is a **new separate Pages target**, GitHub Actions →
Wrangler/Direct Upload after protected-main/test gates. Exact project/account/
output/tool versions must be verified by the receiver owner; this document does
not claim account access or create config. Reproducible build artifact includes
source SHA, manifest and SHA256. PR tests cover existing Cast verification plus
new bootstrap state/security/localization/browser behavior, without production
secrets. Controlled preview is a separate origin, not an implicit HA allowlist.

Promotion uses the exact tested artifact from trusted main, protected environment,
minimum-scoped deploy credential, fixed target/output, concurrency and stale-run
fence. No fork/PR secret access, untrusted workflow artifact promotion, Global API
Key or general DNS/APNs credential. Inventory existing Cast Git-integration
push/preview/production effects before source push: the same repo push can deploy
old Cast even with unchanged bytes. No competing new Git-autodeploy plus Actions
route that bypasses gates; do not overwrite/redirect/delete the existing project,
origin or AppID. Existing settings are not silently changed.

Live acceptance needs immutable deployment and root HTTPS/TLS/redirect/content
and manifest hash/header readback, honest service-unavailable state and unchanged
Cast bytes/origin/privacy headers. Record the actual target, minimal provisioning/
domain binding, current resources, exact effect approval and rollback to prior
tested artifact/binding. A green YAML/preview is not Pages/domain/runtime PASS.
No DNS/deployment/account/plan change is performed by this Core docs assignment.

## One adaptive design: Glass / Soft / Solid

| Tier | Capability/performance admission | Rendering and invariants |
| --- | --- | --- |
| Solid | Safe base on weak or uncertain engines/devices; also explicit fewer-effects/contrast choice | Opaque legible panels, complete authorized content/functions and source links |
| Soft | Necessary CSS support and measured stable bounded rendering | Limited translucency/layers, minimal blur and static highlights; same functions |
| Glass | Feature support plus smooth actual-device and long-running qualification | Restrained blur/gloss/depth; same security, content, controls and rights |

Use maintainable centralized feature checks such as supported CSS/filter features,
media preferences and measured rendering/memory pressure, with conservative
fallback if a check is absent or ambiguous. UA/brand/engine version is diagnostic,
not admission. Use bounded observations without hidden fingerprinting or long-term
performance identity; avoid oscillating tiers, apply cooldown/downshift and a
local accessible **Minder effecten** override. It can reduce effects without
changing guest privileges or functionality. Respect Reduce Motion, contrast and
reduced transparency where supported; unsupported media queries use safe defaults.
QR/code panels are always opaque, still, sharp and high-contrast with quiet zones.
No glare, transforms, blur or motion over scannable content. This is web styling
inspired by Apple glass, never native Liquid Glass or a TLS/crypto downgrade.

Acceptance: actual modern WebKit and Chromium, responsive portrait/landscape,
keyboard/remote/touch/focus/screen reader, en/nl/de/fr/es, all tiers with feature
absence and user overrides, and long-running soak/memory/thermal/reconnect/suspend
behavior on real older TV engines. A UA spoof/desktop screenshot cannot establish
old-TV support or performance. Browser minima and concrete bug exclusions remain
to qualify. An insecure browser gets an explicit unsupported state, not old crypto.

## Browser route versus optional Cast route

| Concern | Primary ordinary browser | Optional Google Cast adapter |
| --- | --- | --- |
| Entry/bootstrap | vibecast.tv/root → real temporary QR destination exchange | Existing sender/device picker/AppID starts or joins registered CAF receiver |
| Code delivery | Standalone bootstrap source/output; no CAF requirement | Existing pinned Cast entry/import and CAF messaging |
| Destination/admission | Verified own HA destination then separate six-digit browser claim approval | Existing sender handoff with Session/Broadcast grant; not an interchangeable display claim |
| Origin | Navigate to own HA for same-origin authorized pages/transport | Static receiver origin must be separately qualified/allowed by HA; preview origin differs |
| Tokens | QR redeem capability, strong browser claim, display grant and guest invitation each distinct | CAF handoff/Broadcast correlation token is neither owner credential nor guest invitation/end grant |
| Session data | Direct HTTPS/WSS HA (with qualified independent local recovery where available) | Direct HA HTTPS/WSS after handoff; never pixels/music/Session relay through sender |
| Shared semantics | Authorized NowPlaying/Flow/Forecast/Moments, guest QR/reactions when implemented/qualified | Same meaning/rights through common renderer, no Cast-specific Flow/Forecast/guest backend |
| Stop/recovery | Browser close only ends that connection/view; share/session controls remain owner-only | Host adapter has sender, receiver-app, idle and handoff lifecycle that needs explicit adaptation |

Existing receiver URL must keep serving its Cast entry, never redirect to the QR
start page. Browser route must not load CAF as a requirement. Cast hardware and
AppID acceptance cannot block independent bootstrap source/build/CD delivery.
Neither route implies music streaming or privileges from another role's token.

## Concrete Cast lifecycle delta

Readback baseline: receiver [CAST_STATUS_ADOPTION_1_1.md](https://github.com/pcvantol/djconnect-vibecast-receiver/blob/cf487797e54ead71bbbe7d4a759e2a1a58e51b1b/docs/CAST_STATUS_ADOPTION_1_1.md)
records view-stop on matching sender `vibecast_stop`, **sender departure,
supersession and unload**; default CAF idle policy remains enabled. Status1.1
has a 15s handshake/recovery deadline and 15s sender status lease, 5s applied-state
heartbeat, strict handoff/Session/generation correlation. Those timers are status/
handshake bounds, not a promise of independent display authority or TV visibility.
Current delivered evidence remains historically exact; no Cast bytes change here.

| Event | Existing v1.1 / required target distinction | Future acceptance |
| --- | --- | --- |
| Owner app closes or sender disappears | Current adapter stops its view; target must preserve DJ Session, other guests and ordinary browser displays. Desired Cast view continuity needs independently valid receiver/HA grant plus actual CAF/idle qualification; it is not yet delivered | Close/crash/background sender and test every independently admitted view/guest plus observed backend state; never disable security/idle policy to fake continuity |
| Explicit receiver/view stop, receiver app unload or CAF idle termination | Clear only this receiver's view/socket/grant/timers; no implicit share-stop, music pause or Session end | Actual CAF/TV idle/app-stop plus server state and other guests; honest lost-presentation status |
| New sender/handoff supersedes old | Retire old handoff/generation and reject late callbacks; optional new authorized view replaces old view only | Late old status/media/stop cannot clear new view or invoke owner effects |
| HA/WSS drops or status lease expires | Freshness/recovery notice; current authorized snapshot and original expiry needed; sender callback alone not success | No stale media revival, private cursor/replay or blind effect retry |
| Owner stops VibeCast share | Explicit owner share authority revokes its displays/guests/invitations; personal DJ Session can continue | Server revocation and all related live connections/media, independent of sender presence |
| Owner ends DJ Session | Explicit owner Session authority revokes all its shares and ends Runtime | Immediate server denial; online clear; offline lease/resume revalidation; no remote pixel-erasure promise |

Product target says app-close must not end the DJ Session/other participants; it
is not a retrospective assertion that senderless Cast already survives CAF idle.
A change from current departure view-stop to future independent Cast presentation
needs separately selected adapter/grant tests, published bytes and real CAF/TV
acceptance. Existing sender deadlines/correlation stay authoritative until that
future qualified change. No physical-PASS from a modeled listener or this matrix.

## Selected receiver slice and separate delivery boundaries

[Receiver#16](https://github.com/pcvantol/djconnect-vibecast-receiver/issues/16),
`DJC-VIBECAST-TV-BOOTSTRAP-CLOUDFLARE-V1-20261015`, is **OWNER_SELECTED_QUEUED**;
executor ACK/current writer admission are not yet observed. The independent
**PUBLIC_WEB_DELIVERY** subset of existing WEB::DISTRIBUTION is selected, and the
receiver-owned **RENDEZVOUS_INTEGRATION** adapter is conditionally selected within
the same #16 once exact TRUST/API service contracts exist. Public delivery
builds real frontend state/adapters/errors, reproducible output/tests/CI and a
controlled Pages route. It may expose an honest unavailable-service production
state pending exact rendezvous, never fake QR or successful pairing.

**RENDEZVOUS_INTEGRATION** depends on WEB::TRUST and API-owned WEB::BOOTSTRAP,
not guest UI or an Apple host. It is receiver adapter integration, not permission
to implement the API producer. **APPLE_HA_ONBOARDING_E2E** additionally depends on
qualified Core WEB::DISPLAY and Apple WEB::OWNER-SCANNER plus public/service
outcomes. **FULL_SHARED_GUEST_ACCEPTANCE** retains the separate WEB::BROWSER
prerequisite (and its GUEST/SHARED producer dependencies). Those Core/API/Apple/
guest producer implementations are not selected by #16; independent public build
is not blocked by them or Cast hardware. Report separately
SOURCE_DELIVERED, CI_QUALIFIED, PAGES_DEPLOYED, DOMAIN_TLS_VERIFIED,
RENDEZVOUS_CONNECTED, APPLE_HA_ONBOARDING_E2E and PHYSICAL_TV_ACCEPTANCE. A public
unavailable-service page cannot close full onboarding or full VibeCast acceptance.

After this exact docsdelta is protected delivered/Finalized and own previous WIP
validly closed, existing receiver lane autonomously performs fresh bootstrap/
writer/resource/effect admission and ACK before first material source change.
No new general start permission is needed. Concrete source/preview/main/Pages/
domain effect gates still apply to its actual candidate. No second receiver
writer, new Core/API/Apple implementation, broad deployment grant or automatic
follow-on slice is created. Return exact design/DAG pin to receiver10/16, Core1101,
Apple87 and API90; service producer must supply explicit fixtures/interface before
real integration. This Core docswriter does not dispatch its own runtime work.

## Decision-to-DAG mapping

| Decision | Canonical contract / existing node | Owner / dependency and acceptance |
| --- | --- | --- |
| vibecast.tv/root RESOLVED | Experience + trust; WEB::DISPOSITION / DISTRIBUTION | Receiver public UI; owner-reported domain, actual domain/TLS readback independent |
| Existing-app exception RESOLVED | Apple guest mode; WEB::APP / DISCOVERY | Core advertises under open admission, Apple both discovery/QR entries; native isolation/permission/choice qualification |
| Glass/Soft/Solid | This tier table + experience; WEB::BROWSER / DISTRIBUTION | Core common renderer and receiver bootstrap; equal functionality, accessibility and long-running actual-engine proof |
| 🤩 preference / 🚀 OPEN | Experience; WEB::REACTIONS | Core subject-bound intake; final set/count/labels not selected, bootstrap independent |
| One source, separate output/Pages/CI | This ownership table; WEB::DISTRIBUTION | Receiver#16 PUBLIC_WEB_DELIVERY selected/queued; pinned Cast bytes preserved |
| Temporary service/wire | Trust; WEB::BOOTSTRAP / TRUST | API proposed producer, explicit reviewed contract; not silently implemented/selected by receiver |
| Optional Cast + lifecycle | This route/lifecycle matrix; WEB::DISPOSITION / BROWSER / JOINT | Existing CAF adapter qualification; no extra backend or browser prerequisite |
| Independent slice then E2E | This delivery table; WEB::DISTRIBUTION subset prerequisites | New exact docsdelta pin precedes independent subset; API/Core/Apple/guest and actual hardware gates apply only to their integration/acceptance phases |

## Primary-source verification

Checked 2026-10-15: Cloudflare [Direct Upload CI](https://developers.cloudflare.com/pages/how-to/use-direct-upload-with-continuous-integration/),
[monorepo targets](https://developers.cloudflare.com/pages/configuration/monorepos/),
[custom domains](https://developers.cloudflare.com/pages/configuration/custom-domains/)
support the proposed separate-target review; they do not prove live account
configuration or grant DNS rights. Google's [receiver core features](https://developers.google.com/cast/docs/web_receiver/core_features)
are a lifecycle/idle reference, not actual CAF acceptance. Apple [TN3179](https://developer.apple.com/documentation/technotes/tn3179-understanding-local-network-privacy)
is the local permission reference; JS-rendered SDK details need rechecking in
Apple implementation. No samples' movable action tags are adopted as CI policy.
