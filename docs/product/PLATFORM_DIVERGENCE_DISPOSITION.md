# CMB-03 — Platform-only Divergence Disposition

**Status:** Assessment complete

**Decision:** `GO_CMB03_PLATFORM_DIVERGENCES_QUALIFIED`

## Result

The canonical divergence register is reconciled against CMB-05 through CMB-12
evidence. Each divergence retains a bounded, objective disposition; none
creates a parity requirement, Runtime ownership change or implementation
authorization.

| Registered divergence | Disposition |
| --- | --- |
| ESP32 constrained controls/lifecycle without rich personal surfaces | Retain intentional constrained profile. |
| ESPHome two-way voice without Session/Profile ownership | Retain platform-specific Voice Host profile. |
| Pi shared/read-heavy profile and independent 10-inch projection | Retain; CMB-05/CMB-06 hardware and shared-profile evidence remains separate. |
| Apple/Windows rich-client differences | Retain non-parity posture; CMB-07 active-Session contract item remains Future Assessment. |
| Universal Receiver/VibeCast differences | Retain distinct Interactive and Ambient experiences; no receiver convergence required. |
| Apple native surfaces and native sharing | Retain Apple-specific realization; no Windows parity or generic sharing platform. |
| Apple local minigames | Retain as unpromoted local candidates; no canonical capability is selected. |
| Historical discovery terminology | Retain only as dated evidence; current Capability Model is authoritative. |
| Central API/website Runtime ownership | Prohibited; any scope expansion requires Architecture Review. |

## Conclusion

`GO_CMB03_PLATFORM_DIVERGENCES_QUALIFIED` confirms that the registered
differences are intentional, separately bounded or explicitly prohibited. The
only unresolved items are already owned by their existing future assessments.
No new qualification item, capability, roadmap priority or implementation is
created.

## Sources

- [DJConnect Capability Model](../../DJCONNECT_CAPABILITY_MODEL.md)
- [Platform Capability Profile Validation](PLATFORM_CAPABILITY_PROFILE_VALIDATION.md)
- CMB-05, CMB-06, CMB-07, CMB-08, CMB-09, CMB-11 and CMB-12 records.
