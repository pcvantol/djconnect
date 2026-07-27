# CMB-01 — Capability Model Pre-flight Adoption Assessment

**Status:** Assessment complete

**Decision:** `GO_CMB01_CAPABILITY_PREFLIGHT_ADOPTED`

## Reference pre-flight

CMB-12 is the reference application of the existing Capability Model process:
it identified a bounded capability family, confirmed Home Assistant as the
canonical owner, classified Apple as a Concrete Host through existing Renderer
and Interaction roles, preserved renderer-safe/privacy constraints, used
cross-repository implementation evidence, recorded maturity and explicit
Future Assessment limits, and made no implementation authorization.

The same sequence is now adopted for future Product and Platform capability
pre-flights:

1. identify one atomic capability and existing canonical owner;
2. establish dependencies, maturity, privacy class and existing projections;
3. map only through Host Roles to applicable Concrete Hosts;
4. record intentional absences and divergence without inferring parity;
5. apply `REUSE → CONFIGURE → EXTEND → NEW` before any implementation GO;
6. conclude one objective decision and record only objective remaining evidence.

This is an adoption of the existing Capability Model and prompt template, not
a new governance framework. It does not change Runtime, architecture, roadmap,
priorities, CI or product behavior.

## Conclusion

`GO_CMB01_CAPABILITY_PREFLIGHT_ADOPTED` closes the sample-pre-flight adoption
record. Future increments continue to use the existing mandatory pre-flight
requirements and repository evidence.

## Sources

- [DJConnect Capability Model](../../DJCONNECT_CAPABILITY_MODEL.md)
- [Host Role Architecture](../../HOST_ROLE_ARCHITECTURE.md)
- [Canonical Engineering Prompt Template](PROMPT_TEMPLATE.md)
- [CMB-12 Apple Native Surface Assessment](../product/APPLE_NATIVE_SURFACE_CAPABILITY_ASSESSMENT.md)
