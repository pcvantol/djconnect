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

## Exact candidate verification — 20 October 2026

PR [#1232](https://github.com/pcvantol/djconnect/pull/1232), rendered source
`3781059ed51fe83ef9d797cf533a1a3630d6f3e7`. README77lines, info23lines.
Both surfaces and all route instructions are part of this candidate; no runtime,
release/tag/version/asset bytes changed. Pairing precedes Profile/backend for
app/local routes; Assist skips pairing. Stable then asks backend → new Profile;
4.0 asks existing/new Profile → provider when needed.

- Full local regression:2669tests PASS,7existing skips,74.397s. Ruff across
  integration/tests PASS; diff whitespace PASS. Seven new docs contract tests.
- Independent editorial preservation review:GO after explicitly tracking the
  ignored maintainer transcript. Committed blob `d8085797b306bb4d5d3d4e0ad2ffa82b54408ab9`.
- Independent technical review:GO after correcting pairing order in all seven
  relevant journeys; no remaining scoped P1/P2.
- Actual public GitHub blob Markdown:12full-page captures, README/info at
  viewport320/375/390px, both system color schemes. Images decoded64×64; no
  article content overflow. Independent full visual review320/390light/dark:GO.
  [Measurements](hacs-readme-1231/results.json), [hashes](hacs-readme-1231/manifest.json),
  [capture script](hacs-readme-1231/capture.mjs).
- Public HACS redirect returned200 and the My Home Assistant instance selector
  with the intended repository/category preserved. No installation followed.
- Current-session host verify MATCH/exit0; no competing Core writer.

### Full mobile captures

| Surface |320px |375px |390px |
|---|---|---|---|
|README light |[view](hacs-readme-1231/README.md-320-light.png)|[view](hacs-readme-1231/README.md-375-light.png)|[view](hacs-readme-1231/README.md-390-light.png)|
|README dark |[view](hacs-readme-1231/README.md-320-dark.png)|[view](hacs-readme-1231/README.md-375-dark.png)|[view](hacs-readme-1231/README.md-390-dark.png)|
|info light |[view](hacs-readme-1231/info.md-320-light.png)|[view](hacs-readme-1231/info.md-375-light.png)|[view](hacs-readme-1231/info.md-390-light.png)|
|info dark |[view](hacs-readme-1231/info.md-320-dark.png)|[view](hacs-readme-1231/info.md-375-dark.png)|[view](hacs-readme-1231/info.md-390-dark.png)|

Installed HACS frontend, actual HA info surface and historical stable-tag render
remain NOT_RUN. The docs/user link targeting protected main becomes available
only after source merge. CI, exact-SHA authorization, protected merge, separate
Finalization and post-merge main/link readback must be recorded from real results.
This source work does not publish a HACS release or alter an installed3.3.1.
Narrative WIP `ff936773c85f1161982eac42a780022b53c4ede1` remains parked and
unfinished; no model attempts were used for this task.
