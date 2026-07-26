# DJConnect Capability Model Backlog

**Status:** Canonical capability-based planning projection

**Owner:** Platform Evolution
**Scope:** Assessment and decision work only; no item presumes new code.

This backlog complements, rather than duplicates,
[`PLATFORM_EVOLUTION_BACKLOG.md`](PLATFORM_EVOLUTION_BACKLOG.md). Every item
starts with a current-state Repository Capability Assessment under
[`DJCONNECT_CAPABILITY_MODEL.md`](DJCONNECT_CAPABILITY_MODEL.md).

| ID | Assessment-first increment | Status | Required first evidence | Outcome boundary |
| --- | --- | --- | --- | --- |
| CMB-01 | Adopt Capability Model assessment in future pre-flights | Planned | sample pre-flight against one existing capability | governance/template only |
| CMB-02 | Validate platform capability profiles | Planned | current contract and host capability inventory | validation only; no parity requirement |
| CMB-03 | Decide each registered platform-only divergence | Planned | divergence register plus owner evidence | promote, retain, converge or retire decision |
| CMB-04 | Re-express Renderer Experience roadmap atomically | Assessed | Receiver, VibeCast and Presentation capability assessment | roadmap/documentation only; see `docs/product/RENDERER_EXPERIENCE_ROADMAP.md` |
| CMB-05 | Assess Pi 4-inch capability profile | Assessed | `docs/product/PI_4_INCH_CAPABILITY_PROFILE_ASSESSMENT.md`; Pi source, contract and shared-device privacy evidence | `GO_PI_4_INCH_PROFILE_PARTIALLY_QUALIFIED`; target-hardware compact-projection and shared-profile visibility evidence remain Future Assessment items; no implementation |
| CMB-06 | Assess Pi 10-inch capability profile | Planned | hardware, privacy and renderer evidence | no inherited 4-inch scope |
| CMB-07 | Analyse Apple–Windows atomic convergence | Planned | contract-level supported/absent matrix | explicit per-capability disposition |
| CMB-08 | Decompose Universal Receiver and VibeCast | Assessed | current Broadcast/receiver evidence | separate host/experience capability records; see `docs/product/RENDERER_EXPERIENCE_ROADMAP.md` |
| CMB-09 | Assess Voice Interaction Host and constrained ESP32 profiles | Planned | HA Voice, Session Start Request and ESP32 contract evidence | role-profile decisions only; no Session ownership or direct host coordination |
| CMB-10 | Onboard future Android and Meta Quest capability profiles | Deferred | product authorization and evidence | profile assessment before any client work |
| CMB-11 | Assess Sharing Experience producers and native Renderer Host realization | Planned | `docs/product/SHARING_EXPERIENCE_ARCHITECTURE.md`, producer privacy evidence and native-client capability inventory | one producer/renderer slice only; no Runtime, Broadcast, public URL or social-service scope |
| CMB-12 | Assess Apple Native Surface capabilities | Planned, after CMB-05/CMB-06/CMB-07 | existing Apple Renderer Host surface inventory and the completed platform-profile evidence | capability inventory and ownership classification only; no surface implementation or Runtime, Renderer, API or product change |

## Rules

- These are not implementation authorizations.
- An item may conclude that the existing capability is reused unchanged.
- A platform-specific absence may be retained without remediation.
- Product Development owns user-facing delivery; Platform Evolution owns only
  the capability-model assessment and governance work recorded here.
- CMB-12 registers the future **Native Surface Integration** family. It is not
  in the current Execution Horizon and does not authorize a native surface or
  implementation candidate.
