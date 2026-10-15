# VibeCast waiting page — bounded HA-dev preview

Owner explicitly requested a separate djconnect branch, DJConnect branding,
glass styling, device/session/VibeCast/code instructions with icon, and publishing
only this HTML to Mac mini HA-dev for testing. This is not a release/merge or
permission to install Python integration changes, restart HA or alter pairing.

Branch: codex/vibecast-waiting-glass-v1. Base:9efd1977768d2574b66c16de9c5d8ba53e9157b1.
Isolated worktree:/private/tmp/djc-vibecast-waiting/source. Active Core Hybrid
writer, its dirty files and branch remain untouched. Non-mutating hostverify MATCH.

Canonical renderer template/style/local-host sources produce the single local
HTML through scripts/build_vibecast.py. Existing DJConnect brand icon embedded
in the artifact: no remote asset request or new dependency. Idle-only branding
and instructional glass panel; three steps and code in en/nl/de/fr/es. Explicit
same-HA-installation reminder, decorative inline VibeCast monitor/Wi-Fi icon,
Reduce Transparency fallback and short/landscape layouts. Google notranslate
metadata avoids browser translation competing with the built-in languages.

No transport, owner permission, live rendering, claims/polling cadence, storage,
Mood or Presence behavior changed. Main renderer inline script is byte-identical
to the installed dev baseline and main. The original complete installed HTML
also equals the main baseline before mutation.

Validation: deterministic local/static build/verification PASS;11 renderer/build
tests PASS with Python3.14 (0.242s). Existing claim/collect/Broadcast test now
checks actual instructions/icon/code and retains no-URL/private-storage tests.
The first invocation used system Python3.9 and failed dataclass slots import;
corrected runtime used. git diff --check PASS.

Deployment plan: retain exact installed HTML backup locally, require its SHA
unchanged, atomically replace only vibecast.html, compare all other integration
file hashes, fetch same-origin page back and inspect actual Pi screen. No HA
restart, release/CI trigger, receiverrepo publish or other integration deployment.
Physical visual result will be recorded separately after the preview is loaded.

Generated candidate HTML SHA256: cef03b2796cb3be9c6473d872de6b6d285f789f7034b93483b084cfead98294e

## Actual HA-dev deployment and physical Pi readback

Source candidate723ba043, separate branch unchanged by other Core work.
Before deployment the dev HTML exactly matched main; session-renderer script
remains byte-identical. Atomically replaced only vibecast.html in the local
homeassistant (HA-dev) container.156 other integration files SHA256-verified
unchanged. No HA restart. Exact previous HTML retained locally at
/private/tmp/djc-ha-dev-running-vibecast-20261015.html. Deployment receipt:
/private/tmp/djc-vibecast-waiting/ha-dev-deployment-receipt.json.

Old HTML SHA256: d72acde5b311e69eebd30ae3a4c47a658f263555da3feed9c709ba426564f4c8
New HTML SHA256: cef03b2796cb3be9c6473d872de6b6d285f789f7034b93483b084cfead98294e

Pi10 fetched HTTP200 through the same configured HA-dev HTTPS origin; served
HTML SHA matches the installed candidate. Refreshed only the verified existing
VibeCast Chromium window. Actual1200x1920 Pi screenshot visually inspected: logo,
glass branding, localized waiting title, three readable instructions, monitor/
Wi-Fi icon, code and same-installation reminder all fit without clipping.
Screenshot is temporary local evidence (contains an ephemeral handoff code),
not committed: /private/tmp/djc-vibecast-waiting/pi-preview.png. This is physical
waiting-page visual proof, not iPad-to-Pi Session/Mood/Presence acceptance.
The iPad UI helper failed enabling automation mode; those E2E cases remain open.
No production HA, Python module, release/CI, pairing, Profile or playback change
was performed for this waiting-page deployment. No push or merge.

## Shared glass cards follow-up

Owner requested the Apple glass/card/corner treatment throughout VibeCast,
including album artwork. Applied Apple geometry tokens:32px outer radius,
8px artwork inset,24px inner image radius,1.25px white border at32% opacity.
Current artwork now has a real wrapper card, square contained image, translucent
blurred surface, highlight and shadow. DJMoment cards use the same symmetric
radius instead of alternate asymmetric speech bubbles. Waiting instructions,
branding, Up Next and its artwork receive matching material/border treatment.
Reduce Transparency and unsupported-blur fallbacks remain readable.

A presentation-only renderer line hides the artwork wrapper when artwork is
withdrawn/unavailable. Existing terminal-authority test now verifies that wrapper
also clears, alongside the private image. All11 build/renderer tests PASS0.239s;
deterministic build verification and diff whitespace PASS.

Offline1200x1920 Chromium preview with synthetic artwork visually inspected:
/private/tmp/djc-vibecast-waiting/glass-cards-preview.png. This exposed an old
fixed image-height rule; height:auto now preserves the square cover/card.
This is a modeled visual preview, not a physical live-session screenshot.

Only generated vibecast.html deployed to HA-dev, no HA restart.162 other
integration source files verified unchanged. Exact receipt and prior HTML backup:
/private/tmp/djc-vibecast-waiting/glass-cards-receipt.json and
/private/tmp/djc-vibecast-waiting/before-glass-cards.html.
Final HTML SHA256:a5b3000f6ac81500e5d1cf05be9e4cfe3926b84692fe9ddf71bd39f8343d7eee.
Physical Pi was already LIVE; captured its before-screen but did not reload its
in-memory receiver authority to replace styling. New styling takes effect on
reload. No playback, pairing, session mutation or receiver-repo publication.
