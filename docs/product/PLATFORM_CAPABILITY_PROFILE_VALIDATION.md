# CMB-02 — Platform Capability Profile Validation

**Status:** Assessment complete

**Decision:** `GO_CMB02_PLATFORM_CAPABILITY_PROFILES_PARTIALLY_QUALIFIED`

## Scope and evidence

This repository-first assessment validates the existing Capability Model, Host
Role Architecture, Client Capability Matrix, Renderer Host Classification, and
CMB-05/CMB-06/CMB-07/CMB-09/CMB-12 assessments. It changes no Runtime, API,
Renderer, host role, capability owner, maturity or platform parity requirement.

## Validated profile model

The canonical relation is unchanged: a capability exists once, Home Assistant
owns Runtime behavior, Host Roles constrain participation, Concrete Hosts
inherit only eligible projections, and Platform Families own neither
capabilities nor roles.

| Concrete-host profile | Validated role composition | Bounded disposition |
| --- | --- | --- |
| Home Assistant | sole Runtime Host | owns Session, Planner, Knowledge, DJMoment, Broadcast, authorization and playback orchestration. |
| Apple iPhone/iPad and macOS | Interaction + Renderer + Rich Personal | personal renderer-safe projections and authorized input only; Apple surfaces are platform-specific. |
| Apple Watch | Interaction + Renderer + Rich Personal | separate companion assessment remains required; it inherits no unselected premium experience. |
| Windows | Interaction + Renderer + Rich Personal | equivalent role participation, not Apple-native-surface parity. |
| Pi 4-inch | Interaction + Renderer + Shared Appliance | compact shared appliance; target-hardware and shared-profile evidence remain separate. |
| Pi 10-inch | Interaction + Renderer + Shared Appliance, Ambient planned | independent shared-wall appliance; concrete hardware and shared-wall evidence remain separate. |
| Universal Receiver | bounded Interaction + Renderer | guest, renderer-safe web presentation only. |
| VibeCast | lightweight Interaction + Renderer + Ambient | separate guest ambient experience, not the Universal Receiver shell. |
| ESPHome Voice Host | Interaction + Voice Interaction | Home Assistant platform-owned voice host; no renderer/personal capability. |
| constrained ESP32 | Interaction + Constrained Device | bounded physical control and appliance lifecycle; no rich personal surface. |

The model is internally consistent with the Client Capability Matrix: Apple and
Windows are personal experiences, Pi/Receiver/VibeCast are bounded shared or
ambient presentation, and voice/constrained hosts are not rich clients. Every
intentional absence remains an absence rather than a defect unless CMB-03
independently records a disposition.

## Qualification limits

The profile architecture is sufficient for current capability participation,
but qualification remains partial because CMB-05, CMB-06, CMB-07 and CMB-12
retain objective evidence items. These are already listed in the Qualification
Register. This assessment creates no new profile, capability or implementation
follow-up.

## Conclusion

`GO_CMB02_PLATFORM_CAPABILITY_PROFILES_PARTIALLY_QUALIFIED` validates the
existing role-to-host profile model and its intentional platform differences.
It authorizes no implementation; CMB-03 is the next separate assessment for
the registered divergence dispositions.

## Sources

- [DJConnect Capability Model](../../DJCONNECT_CAPABILITY_MODEL.md)
- [Host Role Architecture](../../HOST_ROLE_ARCHITECTURE.md)
- [Client Capability Matrix](../../CLIENT_CAPABILITY_MATRIX.md)
- [Renderer Host Classification](../technical/RENDERER_HOST_CLASSIFICATION.md)
- CMB-05, CMB-06, CMB-07, CMB-09 and CMB-12 assessment records.
