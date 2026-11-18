# DJConnect Software Assurance Themes

Status: canonical theme catalog  
Scope owner: `pcvantol/djconnect`  
Builds on: `SOFTWARE_ASSURANCE_PLATFORM.md`

## Purpose

Software Assurance themes define the stable quality domains owned by the
Software Assurance Platform.

Themes are not tools. They are governance categories that let DJConnect decide
which evidence is required, which policies apply, how execution should be
planned and how platform health should be reported.

## Theme 1: Static Quality

Static Quality governs source, configuration and documentation quality before
runtime execution.

Examples:

- formatting;
- linting;
- static analysis;
- CodeQL;
- Semgrep;
- language-specific analyzers;
- configuration validation;
- documentation checks;
- localization static parity where applicable.

Owned questions:

- Is source quality consistent with repository standards?
- Are obvious defects or unsafe patterns caught early?
- Are static checks scoped and reported consistently?
- Are findings classified by quality policy rather than hidden in tool output?

Boundaries:

- Static Quality does not own product behaviour.
- Static Quality does not replace Verification scenarios.
- Static Quality does not decide releases by itself.

## Theme 2: Supply Chain Assurance

Supply Chain Assurance governs dependencies, artifacts, licenses, provenance
and external software risk.

Examples:

- dependency governance;
- SBOM;
- SPDX;
- CycloneDX;
- CVE;
- EPSS;
- KEV;
- provenance;
- artifact integrity;
- license compliance;
- release repository consistency.

Owned questions:

- Which third-party components are present?
- Which vulnerabilities or advisories matter for DJConnect?
- Are licenses compatible with DJConnect distribution?
- Can release artifacts be traced to source and expected build metadata?
- Are checksums, manifests and release notes consistent?

Boundaries:

- Supply Chain Assurance does not choose product dependencies for feature
  reasons.
- Dependency upgrades remain implementation work owned by the affected
  repository.
- License and notice updates must preserve the platform licensing position.

## Theme 3: Dynamic Runtime Assurance

Dynamic Runtime Assurance governs runtime quality characteristics beyond
functional correctness.

Examples:

- performance;
- memory;
- stress;
- chaos;
- fuzz;
- robustness;
- runtime diagnostics;
- timeout behaviour;
- long-running stability.

Owned questions:

- Does the platform remain robust under load, failure or malformed input?
- Are performance and resource signals collected consistently?
- Are runtime diagnostics useful without leaking secrets or personal data?
- Which dynamic checks belong in nightly, release or local profiles?

Boundaries:

- Behavioural expected results remain Verification-owned.
- Runtime implementation fixes remain owned by the affected repository.
- Dynamic Runtime Assurance supplies quality posture and follow-up ownership.

## Theme 4: Execution Strategy And Cost Governance

Execution Strategy and Cost Governance owns how quality work is planned
efficiently across environments.

Examples:

- GitHub-hosted execution;
- self-hosted execution;
- local execution;
- hybrid execution;
- execution profiles;
- cost-aware planning;
- parallelism;
- artifact retention;
- nightly strategy;
- hardware scheduling.

Owned questions:

- Which execution profile is appropriate?
- Which runner or lab should execute the work?
- How much evidence should be retained?
- When should work be parallelized or serialized?
- Which hardware should be reserved for release confidence?
- Which expensive work belongs in nightly rather than PR checks?

Boundaries:

- Execution optimization belongs here.
- The Planning Engine performs concrete optimization.
- GitHub Actions is an execution surface, not the policy owner.

Canonical profiles:

| Profile | Use | Evidence posture |
| --- | --- | --- |
| Economy | Local and early PR feedback. | Summary or structured evidence, short retention. |
| Balanced | Normal development and broad PR confidence. | Structured evidence, representative coverage. |
| Release | Release candidate and production qualification. | Full required redacted evidence, stronger retention. |

## Theme 5: Release Assurance

Release Assurance governs confidence that a release can be promoted, published
or rolled back safely.

Examples:

- release qualification;
- signing;
- promotion;
- rollback;
- release evidence;
- release gates;
- release notes;
- compatibility metadata;
- artifact checksums;
- distribution repository state.

Owned questions:

- Is the release evidence complete?
- Are release artifacts traceable, intact and correctly named?
- Are compatibility, migration and known-limitations notes present?
- Are privacy, security and license obligations satisfied?
- Is rollback or recovery documented where relevant?

Boundaries:

- Release Assurance does not own product roadmap decisions.
- Release gates remain policy-driven.
- Release repositories remain distribution surfaces, not product-logic owners.

## Theme 6: Platform Health

Platform Health is evidence-derived trend reporting across repositories and
quality dimensions.

Health dimensions:

- Functional Health;
- Security Health;
- Supply Chain Health;
- Engineering Health;
- Operational Health;
- Repository Health.

Owned questions:

- Is quality improving, degrading or stable?
- Which repositories carry the most unresolved quality risk?
- Which risks are release-blocking, advisory or backlog candidates?
- Which evidence is stale, missing or contradictory?
- Which investment should be prioritized next?

Boundaries:

- Platform Health supports decision making.
- Platform Health never replaces release policies.
- Health trends do not unblock failed release gates.

## Cross-Theme Rules

All themes follow these rules:

- one canonical owner for quality governance;
- no duplicated evidence;
- no duplicated gates;
- no secrets, raw prompts, raw audio or personal history in quality evidence;
- redaction follows the platform diagnostics and verification standards;
- findings must identify the owning repository or platform subsystem;
- advisory findings should become backlog work when they are not immediately
  fixed;
- implementation requires a future explicit prompt.

## Relationship To Platform Quality Standard

`PLATFORM_QUALITY_STANDARD.md` defines the target quality baseline for every
repository. Software Assurance themes organize how that standard is governed,
planned, evidenced and reported.

The standard says what quality should look like. The Software Assurance
Platform says how quality governance is owned and evolved.

## Decomposition References

The canonical implementation decomposition for these themes lives in:

- `SOFTWARE_ASSURANCE_CAPABILITY_MODEL.md`;
- `SOFTWARE_ASSURANCE_BACKLOG.md`;
- `SOFTWARE_ASSURANCE_DEPENDENCIES.md`;
- `SOFTWARE_ASSURANCE_IMPLEMENTATION_ORDER.md`.

The canonical integration decomposition lives in:

- `SOFTWARE_ASSURANCE_INTEGRATION.md`;
- `SOFTWARE_ASSURANCE_EXECUTION_MODEL.md`;
- `SOFTWARE_ASSURANCE_PLATFORM_HEALTH.md`;
- `SOFTWARE_ASSURANCE_REPOSITORY_MODEL.md`.
