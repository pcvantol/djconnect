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
| CMB-01 | Adopt Capability Model assessment in future pre-flights | Assessed | `docs/governance/CAPABILITY_MODEL_PREFLIGHT_ADOPTION.md`; CMB-12 reference pre-flight and existing Capability Model/template | `GO_CMB01_CAPABILITY_PREFLIGHT_ADOPTED`; existing pre-flight method adopted without new governance or implementation |
| CMB-02 | Validate platform capability profiles | Assessed | `docs/product/PLATFORM_CAPABILITY_PROFILE_VALIDATION.md`; Capability Model, Host Role Architecture, Client Capability Matrix and completed host assessments | `GO_CMB02_PLATFORM_CAPABILITY_PROFILES_PARTIALLY_QUALIFIED`; current role-to-host profiles are consistent; retained host evidence remains Future Assessment; no implementation |
| CMB-03 | Decide each registered platform-only divergence | Assessed | `docs/product/PLATFORM_DIVERGENCE_DISPOSITION.md`; canonical divergence register and completed host assessments | `GO_CMB03_PLATFORM_DIVERGENCES_QUALIFIED`; differences are retained, separately assessed or prohibited; no implementation |
| CMB-04 | Re-express Renderer Experience roadmap atomically | Assessed | Receiver, VibeCast and Presentation capability assessment | roadmap/documentation only; see `docs/product/RENDERER_EXPERIENCE_ROADMAP.md` |
| CMB-05 | Assess Pi 4-inch capability profile | Assessed | `docs/product/PI_4_INCH_CAPABILITY_PROFILE_ASSESSMENT.md`; Pi source, contract and shared-device privacy evidence | `GO_PI_4_INCH_PROFILE_PARTIALLY_QUALIFIED`; target-hardware compact-projection and shared-profile visibility evidence remain Future Assessment items; no implementation |
| CMB-06 | Assess Pi 10-inch capability profile | Assessed | `docs/product/PI_10_INCH_CAPABILITY_PROFILE_ASSESSMENT.md`; architecture, shared QML foundation and absent 10-inch implementation evidence | `GO_PI_10_INCH_PROFILE_PARTIALLY_QUALIFIED`; concrete 10-inch appliance and shared-wall projection evidence remain Future Assessment items; no implementation |
| CMB-07 | Analyse Apple–Windows atomic convergence | Assessed | `docs/product/APPLE_WINDOWS_ATOMIC_CONVERGENCE_ASSESSMENT.md`; Apple/Windows source and contract-level supported/absent matrix | `GO_CMB07_APPLE_WINDOWS_CONVERGENCE_PARTIALLY_QUALIFIED`; rich-renderer active-Session contract disposition remains Future Assessment; no implementation |
| CMB-08 | Decompose Universal Receiver and VibeCast | Assessed | current Broadcast/receiver evidence | separate host/experience capability records; see `docs/product/RENDERER_EXPERIENCE_ROADMAP.md` |
| CMB-09 | Assess Voice Interaction Host and constrained ESP32 profiles | Assessed | `docs/product/VOICE_INTERACTION_HOST_ESP32_CAPABILITY_PROFILE_ASSESSMENT.md`; Home Assistant Voice Host and native LilyGO appliance evidence | `GO_CMB09_VOICE_HOST_PROFILE_QUALIFIED`; the shared Home Assistant Voice Host and DJConnect-owned appliance profiles are distinct, bounded and implementation-free |
| CMB-10 | Onboard future Android and Meta Quest capability profiles | Deferred | product authorization and evidence | profile assessment before any client work |
| CMB-11 | Assess Sharing Experience producers and native Renderer Host realization | Assessed / implementation completed | `docs/product/SHARING_EXPERIENCE_ARCHITECTURE.md`, PR #490/#492 assessment-refinement evidence and `djconnect-app` PR #50 native-share evidence | `GO_SHARING_IMPLEMENTATION` was realized only as Track Insight → Apple Native Sharing; no generic sharing platform, Runtime, Broadcast, public URL or social-service scope |
| CMB-12 | Assess Apple Native Surface capabilities | Assessed | `docs/product/APPLE_NATIVE_SURFACE_CAPABILITY_ASSESSMENT.md`; canonical renderer boundaries and `djconnect-app` native-surface inventory | `GO_CMB12_APPLE_NATIVE_SURFACES_PARTIALLY_QUALIFIED`; existing Apple Session, Information and navigation surfaces are classified; active-Session projection and lifecycle-invocation qualification remain Future Assessment; no implementation |

## Rules

- These are not implementation authorizations.
- An item may conclude that the existing capability is reused unchanged.
- A platform-specific absence may be retained without remediation.
- Product Development owns user-facing delivery; Platform Evolution owns only
  the capability-model assessment and governance work recorded here.
- CMB-12 assesses the **Native Surface Integration** family. It authorizes no
  native surface or implementation candidate; its two remaining qualification
  items remain separate Future Assessments.
