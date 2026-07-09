# Epic Context Template

Use this template before starting an implementation epic.

## Mission

Describe the Epic in one or two paragraphs.

Include:

- what user or platform problem this Epic solves;
- which foundation laws or principles it advances;
- which repositories may be affected;
- what should be true when the Epic is complete.

## Foundation documents to read

Read the canonical foundation first:

- `FOUNDATION_INDEX.md`
- `DJCONNECT_CONSTITUTION.md`
- `PRODUCT_VISION.md`
- `DESIGN_FOUNDATION_VERSION.md`
- `DESIGN_PRINCIPLES.md`
- `ARCHITECTURE_PRINCIPLES.md`
- `DOMAIN_MODEL.md`
- `CLIENT_CAPABILITY_MATRIX.md`
- `PRODUCT_LANGUAGE.md`
- `PLATFORM_PRINCIPLES.md`
- `PLATFORM_GOVERNANCE.md`
- `PLATFORM_QUALITY_STANDARD.md`
- `PLATFORM_BACKLOG.md`
- `REPOSITORY_OWNERSHIP.md`
- `INNOVATION_LAB.md`
- `ADR_INDEX.md`
- relevant files under `docs/adr/`
- `IMPLEMENTATION_GUIDELINES.md`
- `IMPLEMENTATION_ROADMAP.md`

## Discovery documents to read

Read relevant discovery outputs:

- `PLATFORM_DISCOVERY_REPORT.md`
- `docs/discovery/README.md`
- repository-specific reports under `docs/discovery/`
- `docs/discovery/TECHNICAL_DEBT_REGISTER.md`
- `docs/discovery/PRODUCT_DEBT_REGISTER.md`
- `docs/discovery/CI_CD_REVIEW.md`
- `docs/discovery/SECURITY_PRIVACY_REVIEW.md`
- `docs/discovery/RELEASE_PROCESS_REVIEW.md`

## Working style

State how the Epic should be worked.

Default:

- read before changing;
- design before implementation;
- split large work into mergeable phases;
- keep every phase compiling;
- keep every phase testable;
- update docs with code;
- avoid unrelated refactors;
- avoid repo-local product truth that conflicts with the canonical foundation.

## Commit strategy

Describe how commits and PRs should be shaped.

Default:

- one branch per phase where practical;
- small commits grouped by architecture layer;
- avoid mixing unrelated repositories in one commit;
- commit docs/tests/contracts with the implementation they explain;
- prefer several focused PRs over one broad PR.

## Breaking changes policy

State whether backwards compatibility is required.

Default for pre-release platform architecture:

- breaking changes are allowed when they improve long-term platform quality;
- breaking changes must be explicit, documented and tested;
- migrations or cleanup paths must be described where user data, tokens or pairing state are affected.

## Definition of success

Describe measurable success criteria.

Include:

- architecture outcomes;
- product outcomes;
- repository outcomes;
- tests;
- documentation updates;
- migration or compatibility outcomes;
- what must be true before the next Epic can begin.

## What is explicitly OUT OF SCOPE

List work that must not happen in this Epic.

Examples:

- unrelated UI redesign;
- unrelated provider support;
- release packaging changes;
- cloud entitlement work;
- runtime refactors outside the phase boundary;
- speculative features not required by this Epic.
