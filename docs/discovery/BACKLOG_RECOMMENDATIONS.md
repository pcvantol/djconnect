# Epic 2 Backlog Recommendations

These recommendations are actionable backlog candidates discovered during Epic 2. They are not implementation work.

## P0

### Epic 3 — Profile Architecture

Implement DJConnect Profile as the runtime identity boundary before major new features.

Deliverables:

- profile storage;
- central profile resolver;
- device-to-profile mapping;
- HA user hint mapping;
- shared/room/guest profile support;
- Music DNA and Ask DJ history migration from user/device keys to Profile;
- profile privacy modes;
- profile export/import contract;
- client capability updates;
- tests for shared-device privacy.

### ADR-0007 — Central API as trust/relay boundary

Accept or revise ADR-0007 before central API expands into entitlement, profile cloud or sync.

## P1

### Insight Feed Architecture

Promote ADR-0005 and design the normalized Insight Feed before adding more Track Insight, Lyrics Explain, Discover or VibeCast-specific contracts.

### Client Capability Parity

Create a parity matrix for Apple, Windows, Pi and ESP32 with required, optional and forbidden capabilities by class.

### Foundation Sync Across Repos

Update every repo's AGENTS guidance to point to `FOUNDATION_INDEX.md`, `PLATFORM_PRINCIPLES.md`, `REPOSITORY_OWNERSHIP.md` and accepted ADRs.

### Release Repository Hygiene

Refresh public release repo READMEs, add AGENTS files, clarify licenses and add or document artifact validation.

### Website Product Language Audit

Audit public pages and release-note templates against `PRODUCT_LANGUAGE.md`, especially `DJConnect Profile`, `Music Backend`, Community/Personal and optional Cloud language.

## P2

### Contract Fixture Compatibility Suite

Promote the existing HA client fixtures into an explicit cross-client compatibility suite with versioned fixture manifest and client conformance status.

### Distribution Strategy

Define TestFlight, App Store, Microsoft Store, website download and public release repository responsibilities before broader public launch.

### Feature Flag Framework

Implement platform-wide feature maturity and capability gating after Profile Architecture.

### Local Dirty-Workspace Hygiene

Add audit instructions for generated/derived folders and local dirty worktrees so future platform discovery runs are reproducible.
