# Read-only Developer Overlay Pre-Flight

## Decision

`GO_E2E_HARNESS_ONLY`

The original shipping-overlay decision was narrowed by the
[Delivery Guard Pre-Flight](DEVELOPER_OVERLAY_DELIVERY_GUARD_PREFLIGHT.md).
The next separately authorized implementation may add only an **E2E-only,
process-local read-only overlay** composed by the existing Universal Receiver
Browser E2E harness. It is not a product capability, public-release requirement,
shipping development build feature or Golden Qualification authority.

## Purpose and release policy

The overlay is Verification Support under Platform Evolution. It exists only in
the E2E harness to aid deterministic observation. It is absent from the served
Receiver, release artifact and public-release scope, and is never a user-facing
feature.

It may project existing authorized data and locally known connection state. It
must never offer controls, send mutation frames, change a Session, influence the
Planner or Capability Policy, execute a Golden Scenario, or affect a
qualification result.

## Repository reconciliation

| Existing provision | Classification | Evidence and resulting boundary |
| --- | --- | --- |
| Universal Receiver Broadcast snapshot and events | Fully fitting | `DJBroadcastState.as_dict()` already supplies renderer-safe Session, Planner summary, Flow, DJMoment and Broadcast watermark fields through the existing read-only subscription. Reuse it unchanged. |
| Universal Receiver page | Partially fitting | The page already keeps an in-memory snapshot and local reconnect state, but intentionally renders a product surface and has no diagnostics. A future overlay may be a development-only presentation layer over that same in-memory projection; it must use a curated field allowlist rather than object dumps. |
| Universal Receiver Browser E2E observer | Partially fitting | It proves snapshot-first delivery, ordered events, reconnect, Runtime end and cleanup without retaining Browser data. It is a useful focused test host, but is not a live diagnostics channel or qualification authority. |
| Immutable Developer Session Capture and Golden Qualification | Partially fitting | They provide bounded, redacted scenario evidence only. They cannot become a live Session inspector, second capture model or overlay data source. |
| Home Assistant config-entry diagnostics | Conflicting as an overlay source | It is support diagnostics, not renderer projection; its redaction boundary protects credentials and private data. It must not be exposed through a Renderer or repackaged as overlay data. |
| Runtime, Planner, Knowledge and DJMoment internals | Conflicting | Their objects, planning candidates, prepared knowledge, Profile context and memory are server-owned. The overlay must not read, serialize or derive them. |
| DJ Brain capability registry and Profile policy | Partially fitting | Registry metadata is immutable, but active policy is Profile-owned. No active policy, allowed-capability list or capability-selection data is currently a renderer-safe projection; do not expose it in this slice. |
| Current capability discovery | Partially fitting | Existing capability discovery advertises client and transport support, not developer-overlay state. Do not add a new HTTP or WebSocket capability contract for this slice. |
| Feature flags | Missing | Platform governance defines feature-flag expectations, but no overlay flag exists. A future implementation needs a development-delivery guard with production default off; it must not be a Profile, Runtime or Planner toggle. |

## Safe projection contract

The future overlay may consume only these already-projected values and local UI
state:

| Area | Permitted read-only values |
| --- | --- |
| Session | `session_id`, Runtime state and selected mood |
| Planner summary | planning state, current direction, Session Direction and planning horizon |
| DJMoment | current renderer-safe Moment identity and type only |
| Session Flow | flow revision and current item count |
| Broadcast | existing snapshot watermark and started-at metadata |
| Transport | locally observed WebSocket connection, reconnect and snapshot-received state |

The future overlay must not render raw JSON or internal object dumps. Start
strategy, Persona, selected capability, capability availability, Knowledge
source/fallback details, Silence causes, Profile data, Music DNA, credentials,
provider payloads, renderer capabilities, host identity and remote/local
classification have no safe existing projection for this slice. Their absence
is intentional and must remain visible rather than inferred.

## Architecture and positioning

The least invasive placement is an **E2E-only composition in the existing
Universal Receiver Browser E2E harness**. The served Receiver page remains
unchanged. It is not platform-wide, Apple-only, a Home Assistant diagnostics
panel, a shipping development build or a new Renderer Host.

The Delivery Guard Pre-Flight found no existing safe build-time or asset-delivery
guard. A URL parameter, Home Assistant service, config option, feature flag that
changes server behavior, or client-to-server control remains unauthorized.

## Verification and governance

The overlay has no direct Golden Scenario behavior. It **protects** the existing
observer boundary for `SI-GOLDEN-001` through `SI-GOLDEN-006`: it consumes the
same snapshot/event sequence but neither executes, captures nor validates a
scenario. Headless Golden Qualification remains complete without it; the
Structural Invariant Validator remains the sole PASS/FAIL authority.

Focused future evidence must prove the overlay is unavailable by default in a
production delivery, contains no controls or outbound mutation path, renders
only the allowlisted projection fields, redacts/omits excluded data, preserves
the existing Receiver reconnect and Runtime-end behavior, and has no effect on
Golden Qualification reports or CI advisory/blocking semantics.

## Explicit exclusions

No Runtime, Planner, Knowledge Engine, DJMoment, Session Flow, Broadcast,
Capability Registry, HTTP API, WebSocket API, Golden Scenario, renderer
ownership, playback or product behavior changes are authorized by this
assessment. No developer overlay implementation is included here.
