# HACS README consolidation — Core1231

## Source and release matrix

Audit20October2026, protected baseline8b221d07fe2215d9516d18fe92c832332c7a16ab.
Main and const report4.0.0-rc.1; public integration stable isv3.3.1. The repository
GitHub latest-release endpoint instead reports onboarding-v4.0.0. That is a
separate developer package, not a HACS integration-version claim. Historical tags
and release artifacts remain immutable. No release/install is performed here.

| Topic | Integrationv3.3.1 source | Main4.0.0-rc.1 source |
|---|---|---|
| Assist setup | Any pipeline with STT and TTS | Selected/preferred pipeline with available conversation agent; speech optional for setup |
| Profile | Backend before new Profile | Existing Profile choice/reuse or new Profile before provider |
| Music | Spotify Direct, Music Assistant, Later/manual | The same choices; reused Profile retains its connection |
| Spotify | Premium, own Client ID, external HTTPS, exact wizard redirect | Same; no Client Secret |
| Music Assistant/Later | No DJConnect Spotify OAuth requirement | No DJConnect Spotify OAuth requirement |
| Windows | Legacy selectable choice | Retired ingress, never new pairing |
| Branding | Historical release text retained | Approved BrandV2, Your music. Your DJ. |

The assignment's tentative Later/manual distinction was corrected from actual
stable source609–618/2161–2164; it is not new in4.0. Current config flow source
1084–1104,2014–2057,2168–2294,2364–2458 was independently read. Stable Assist
preflight1080–1092 and Profile2340–2364 differ. External HTTPS is a Spotify-OAuth
requirement, not a blanket prerequisite for every route.

## Relocation and preservation

- APNs original README text, retry/error handling and unique info diagnostics:
  technical/PUSH_NOTIFICATIONS.md; original reconstruction explicitly historical.
- Backend-switch preservation/revision and entities: technical/ENTITIES_AND_SUPPORT.md.
- VibeCast rich text/emoji/proxy/genre/TTL and Discovery sections already have
  authoritative API_CONTRACT sections; docs index links them instead of duplicating canon.
- Verification, standalone Engineering Platform and Software Assurance: existing
  canonical index links from docs/README.md, without the HACS technical essay.
- Entire original maintainer checklist: verbatim historical transcript in
  docs/release/maintainer.md; current protected governance takes precedence.
- User requirements and steps: docs/user; five-language guidance ships together.

## Brand consumption and page scope

Only the existing approved transparent128px PNG mark from protected7e14e597 is
consumed at64px, with normal theme-aware heading text. No binary/generator/style
is altered. The same absolute immutable PNG avoids relative-image failures in
HA and avoids depending on picture/source or SVG selection. Its transparency
and glass edge are already in the approved asset; no CSS button or border added.
HACS render_readme stays true, manifest documentation stays the repository root.
README has a clickable deeplink; info uses absolute links for HA's rendering context.

## Validation and limits

Source checks, actual GitHub Markdown rendering and mobile light/dark captures
are recorded separately below. A public deeplink landing page does not prove an
installed HACS flow or selected HA authorization. Actual HACS installed frontend
and stable-tag runtime/rendering are not claimed until directly exercised.
Source/PR/main/release/native/installed/physical acceptance remain separate.
