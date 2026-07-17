# Platform Release Observatory — Canonical Design

**Status:** Design complete / implementation backlog
**Owner:** Platform Evolution
**Decision:** `PLATFORM_RELEASE_OBSERVATORY_DESIGN_ESTABLISHED`
**Scope:** Local-only, read-only release observation; no execution capability

## 1. Purpose and users

The Platform Release Observatory gives the Platform Executive and Release Train Engineer a factual, traceable view of DJConnect publication and rollout state. It complements the frozen Platform Release architecture; it neither changes nor operates that architecture.

Its primary users ask: What is publicly published now? What is deployed internally now? What artifacts are currently available? Which rollouts exist or existed, and what is each rollout/component state? What is blocked, waiting, or requires an owner action? Which objective evidence supports each derived conclusion?

The Observatory answers from retained facts and explicit derivation rules. It does not infer success from prose, approval intent, or missing evidence.

## 2. Scope and boundaries

In scope are complete platform rollouts, component rollouts, internal production deployments, public distribution and app-store publication, artifact publication, current and historical state, GitHub repositories/commits/pull requests/Actions, approved manifests, deployment and smoke evidence, repository status/release reports, and supported factual external publication or review sources.

Out of scope are deployment, approval, manifest changes, workflow triggers, release gating, rollback, remote hosting, multi-user authentication, secret storage, and product analytics. The Observatory is read-only with respect to release execution. It does not replace the Platform Release Runtime, GitHub Actions, the existing release architecture, or existing evidence producers.

## 3. Operating model

The proposed application runs only on the maintainer MacBook and conceptually contains a Node-based collector and local server, a local SQLite database, and a reactive browser dashboard. It has no authentication requirement because it is local-only, but the server must bind to loopback by default. Any non-loopback bind must require an explicit local operator choice and display an exposure warning; it is not a supported remote service mode.

`collect` owns source inspection, current and historical evidence discovery, normalization, idempotent fact/history updates, derived-state recalculation, and collection provenance/timestamps. `run` owns only the local backend and dashboard, reading the persisted SQLite data. `investigate` may become an alias or a future diagnostic mode for `collect`; it must not introduce a second, indistinguishable command responsibility.

## 4. Source hierarchy and provenance

The collector ranks factual sources in this order: approved release/deployment manifests; immutable repository evidence; commits/tags; pull requests; GitHub Actions runs/jobs/steps and retained artifacts/evidence reports; deployment and smoke evidence; repository status and management summaries; artifact and distribution repositories; then supported public-store/publication status sources. Stronger machine-readable evidence prevails over weaker documentation or management text. Documentation, comments and summaries never override a stronger fact.

Every `EvidenceFact` retains source type, repository or external channel, stable source identifier, safe source URL, source timestamp, collection timestamp, applicable commit SHA or artifact identity, confidence/evidence-completeness classification, and parser/schema version. Derived states retain references to their contributing facts. Conflicts are recorded explicitly and fail closed; the collector must never silently choose the convenient version or status.

## 5. Canonical domain model

| Entity | Responsibility |
| --- | --- |
| `PlatformComponent` | A repository-owned release participant with capability and ownership identity. |
| `DistributionChannel` | An internal deployment, artifact repository, public download, or supported store channel. |
| `ArtifactRelease` | An identified artifact with version, source SHA, checksum and evidence links where available. |
| `ObservedDeployment` | A fact about a deployed component/target, distinct from a release definition. |
| `ObservedPublication` | A fact about an available artifact or public/store publication. |
| `Rollout` | A platform or component coordination record whose state is derived from facts. |
| `RolloutComponent` | A component's participation in one rollout and its ordered, characteristic steps. |
| `RolloutStep` | One component-specific observed or planned progress boundary. |
| `EvidenceFact` | An immutable normalized observation with provenance. |
| `OwnerAction` | A safe link to an accountable action, approval, or external-review follow-up. |
| `CollectionRun` | A bounded collection attempt, source coverage, freshness and outcome. |

A platform rollout coordinates zero or more components; a component rollout is one component's rollout record. An internal deployment, public publication and artifact publication are observed facts, not synonyms for a release definition or a successful rollout. A rollout can reference them without asserting that every component has the same build, review, deployment or smoke steps.

## 6. Uniform rollout status model

| Status | Meaning and entry evidence | Exit / terminal character |
| --- | --- | --- |
| `DEFINED` | A rollout definition exists but no executable/progress evidence exists. | First-step evidence; non-terminal. |
| `NOT_STARTED` | Required steps are known and no step has started. | Started or waiting evidence; non-terminal. |
| `IN_PROGRESS` | A supported step is active and no stronger condition applies. | Completion, waiting, paused, blocked or aborted evidence; non-terminal. |
| `WAITING_FOR_OWNER_ACTION` | Objective evidence identifies an accountable owner action. | Action resolution or stronger condition; non-terminal. |
| `WAITING_FOR_APPROVAL` | An internal approval is required and pending. | Approval or stronger condition; non-terminal. |
| `WAITING_FOR_EXTERNAL_REVIEW` | A supported external channel reports pending review. | External decision or stronger condition; non-terminal. |
| `PAUSED` | A supported pause/defer record exists without a failure. | Resume, abort, or blocker evidence; non-terminal. |
| `BLOCKED` | A required step has failed, is contradictory, or has unmet blocking evidence. | Objective unblocking/retry evidence; non-terminal. |
| `ABORTED` | A supported cancellation/withdrawal fact exists. | Terminal. |
| `COMPLETED_WITH_WARNINGS` | Required completion evidence exists and accepted, non-blocking warnings remain. | Terminal. |
| `SUCCEEDED` | All required components and steps have objective successful evidence, with no unknown or contradictory required evidence. | Terminal. |

For a component, precedence is `ABORTED`, then `BLOCKED`, then external review, internal approval, owner action, `PAUSED`, `IN_PROGRESS`, `NOT_STARTED`, and `DEFINED`; a completed component is `COMPLETED_WITH_WARNINGS` when accepted warnings exist, otherwise `SUCCEEDED`. A platform aggregation exposes every component result and uses the strongest unresolved required component condition under the same order. It never hides a failed component behind successful components. Unknown, stale, missing or contradictory required evidence prevents `SUCCEEDED`; a pending external review is distinct from waiting for internal owner approval.

## 7. Step and duration model

Each step has a stable identifier, component, step type, expected predecessor, started/completed UTC timestamps when objectively evidenced, current derived status, evidence references, optional owner-action link, safe management summary or GitHub comment reference, and warning/blocker classification. All absolute timestamps are stored in UTC and displayed in the local timezone. Relative duration is calculated only between objectively evidenced boundaries. Missing boundaries remain unknown, never zero or fabricated.

## 8. Dashboard requirements

The dashboard lists current and historical rollouts newest first by default. It filters/groups by complete platform rollout, component rollout, internal production, public publication, artifact publication, derived status, component, and time period.

Selecting a rollout shows one horizontal workflow row for every participating component—every component row for a platform rollout—with connected step nodes. Completed, active, waiting, blocked, aborted and not-started steps have distinct representations, and observed progress is distinct from planned future steps. Each node exposes local timestamps, relative durations, safe metadata, owner-action/approval links where available, and links to underlying GitHub or publication evidence. Row count is derived from rollout definition and repository ownership, never a fixed expected component count.

## 9. Historical collection

`collect` accepts a configurable time range and enumerates repositories and channels from canonical ownership/configuration. It supports pagination, rate-limit awareness, reprocessing, late-arriving facts, and idempotent updates through stable source identities plus parser versions. Corrected derivations do not delete original facts. Unavailable, expired or pruned GitHub evidence is represented explicitly with its collection provenance.

Historical reconstruction is bounded by source retention and evidence availability. The Observatory may reconstruct supported history after an extended interval, but must never fabricate an absent historical step.

## 10. Evidence and timing contract gap

Existing manifests, workflow runs, deployment evidence and smoke evidence are valuable factual sources, but durable step-duration analysis requires future machine-readable instrumentation in CI, deployment, smoke and publication flows. The minimum future evidence contract is: rollout identifier, component identifier, step identifier/type, event status and UTC timestamp, source repository, workflow/run/job/step identity, candidate or release identifier, commit SHA, artifact identity/checksum where applicable, evidence schema version, and a safe owner-action/approval reference where applicable.

Adding that instrumentation is a separate future engineering increment. This design changes no workflow or evidence producer.

## 11. Security and privacy

The database, logs and dashboard exclude secrets, access tokens, environment secret values, prompt contents, private credentials, raw authorization headers, and unnecessary personal data. Collection credentials remain outside SQLite and logs in the platform's ordinary local credential mechanism. Redaction is the default; the collector fails closed when it cannot determine that content is safe to persist.

## 12. Failure and consistency behaviour

Source unavailability, partial collection, GitHub rate limits, expired artifacts, conflicting versions/states, stale evidence, unsupported schemas, missing component evidence and unavailable external-review state are explicit collection outcomes. A partial or stale run remains visible and is never shown as fully current. The dashboard shows collection freshness and last successful collection time. Conflicts preserve all facts and block a success conclusion until objective reconciliation is available.

## 13. Proposed delivery increments

1. **Evidence and timing contract** — add and qualify machine-readable rollout-step and duration evidence in the owning CI, deployment, smoke and publication flows.
2. **Collector and persistence** — implement source adapters, normalization, provenance, derived status, historical collection and SQLite persistence.
3. **Local dashboard** — implement rollout list/filtering, component workflow visualization, evidence details, owner-action links, local timestamps and durations.

Each is a bounded future prompt and reviewable pull request. No increment is authorized by this design alone.

## Deferred work

The evidence instrumentation gap is deliberately deferred to delivery increment 1, owned by the relevant CI/deployment/smoke/publication flows. The collector and dashboard remain deferred to increments 2 and 3. Their priority is P2 because current Platform Release operational records remain authoritative and the design does not block Product Development or alter the Platform Release 3.3 sequence.

## Design evidence

This design is grounded in the existing release architecture ([`PLATFORM_RELEASE_ARCHITECTURE.md`](../release/PLATFORM_RELEASE_ARCHITECTURE.md)), approved current-main manifest ([`PLATFORM_3_3_CURRENT_MAIN_MANIFEST_PROPOSAL.json`](../release/PLATFORM_3_3_CURRENT_MAIN_MANIFEST_PROPOSAL.json)), deployment evidence contract ([`PLATFORM_RELEASE_DEPLOYMENT_EVIDENCE.md`](../release/PLATFORM_RELEASE_DEPLOYMENT_EVIDENCE.md)), and redacted post-deployment smoke evidence contract ([`POST_DEPLOYMENT_SMOKE_EVIDENCE_SCHEMA.md`](../release/POST_DEPLOYMENT_SMOKE_EVIDENCE_SCHEMA.md)). It is the detailed capability design for the active Platform Evolution backlog item, not an implementation or release authorization.
