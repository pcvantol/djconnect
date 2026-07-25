# Developer Overlay Delivery Guard Pre-Flight

## Decision

`GO_E2E_HARNESS_ONLY`

The Read-only Developer Overlay is narrowed to **E2E-only observability
tooling**. Its only authorized future implementation is a process-local
composition in the existing Universal Receiver Browser E2E harness. It is not
a shipping development build feature, a Receiver capability or a product
renderer surface.

## Reconciliation matrix

| Mechanism | Owner and phase | Production / release / HACS exposure | E2E usability and security boundary | Cache and Receiver impact | Classification |
| --- | --- | --- | --- | --- | --- |
| Universal Receiver static page | HA integration; served at Runtime from `custom_components/djconnect/universal_receiver.html` | The page is always present in the integration directory; the release workflow archives the complete directory and HACS uses the integration source. | Existing page consumes only the renderer-safe Broadcast token subscription. No development guard exists. | `no-store` response; one production page remains. Adding a development asset here would ship it. | Production-risk |
| Frontend build / compile-time guard | No owner or build phase exists; the repository has no frontend package or bundler configuration. | No production removal step or generated asset path exists. | Cannot be deterministically selected without introducing build tooling. | Would create a new delivery architecture and artifact qualification need. | Not available |
| Separate development asset | No current static-resource registration or non-production asset package exists. | Any file under `custom_components/djconnect` is included in the release tarball; no HACS/release exclusion convention exists. | Could be test-only only if outside the integration package, in which case it is an E2E fixture rather than a Receiver asset. | No safe shipping route; a test fixture leaves the Receiver unchanged. | Partially fitting only as E2E harness input |
| Existing Browser E2E harness | Verification infrastructure; process-local Node VM reads the Receiver source directly from the checkout. | Harness module and its tests are outside the release artifact, which packages only `custom_components/djconnect`; no browser state or asset is served. | Reuses an existing authorized Broadcast subscription; real tokens remain outside the Node input, and no output, artifact, screenshot, trace, HAR or video is retained. | No cache and no production Receiver impact. | Safely fitting |
| Existing development-host signal | Local machine bootstrap and lab ownership only. | Not supplied to the Receiver or release artifact. | It is not a page-delivery signal and using it would require new server behavior. | Cannot guard a static page without an unauthorized delivery change. | Not available |

## Architectural result

The single static production Receiver remains unchanged. The Home Assistant
release artifact packages `custom_components/djconnect` as a whole, so neither a
compile-time development variant nor an integration-resident development asset
has an existing safe exclusion path. No build tooling, static-resource
registration, cache policy, HACS behavior or release packaging is changed.

The authorized overlay is therefore not a shipping development overlay. It may
be composed only by the existing Browser E2E harness from the already-available
renderer-safe snapshot/event data and locally observed transport lifecycle. It
must remain process-local, default-absent from the served page, token-safe and
subordinate to headless Golden Qualification.

## Boundaries

The E2E-only tooling may not add an HTTP route, WebSocket command, Broadcast
field/event, Runtime state, diagnostics model, browser persistence, control or
qualification authority. It may not expose Profile data, capability policy,
registry metadata, Start Strategy, Persona, renderer identity, credentials or
provider data. It protects, but does not execute, capture or validate,
`SI-GOLDEN-001` through `SI-GOLDEN-006`.

## Exactly one next step

Authorize one bounded **E2E-only Developer Overlay harness implementation**:
compose an allowlisted read-only panel in the existing headless Receiver
harness, test its presence only in the harness and its absence from the served
Receiver/release artifact, and retain the existing Browser E2E privacy,
transport and qualification boundaries.
