# Implementation Phase Template

Use this template for every phase inside an implementation epic.

## Prompt governance

- Lifecycle state: `Draft` (change to `Active` only when explicitly
  authorized).
- Engineering increment: state the one coherent objective.
- Dedicated branch: name the branch for this increment.
- Pull request contract: exactly one independently reviewable pull request;
  merging is a separate explicit decision.
- Scope protection: identify adjacent work that this prompt must not overlap.

## Phase goal

State the goal of this phase.

Include:

- what changes in this phase;
- what remains unchanged;
- why this phase is the next smallest mergeable unit.

## Architecture

Describe the architecture boundary.

Answer:

- which domain object owns the new or changed state;
- which repository owns the behavior;
- whether this touches Profile, Device, Music Backend, Session, Feature Flag, Insight Feed or Renderer/Client;
- how this avoids duplicate contracts or business logic;
- how this phase keeps the next phase possible.

## Deliverables

List concrete deliverables.

Examples:

- storage model;
- resolver;
- API contract;
- client rendering update;
- migration;
- tests;
- docs;
- ADR proposal.

## Definition of Done

The phase is done when:

- implementation is complete for the stated scope;
- code compiles;
- expected tests pass;
- documentation is updated;
- privacy/security constraints are checked;
- no out-of-scope runtime changes are included;
- the PR is independently mergeable.

## Completion

Work only on the dedicated branch. Keep the scope focused. Produce exactly one
reviewable pull request. Update canonical documentation where required.

Before stopping, update:

- Repository Status;
- Management Summary;
- Prompt Index.

Validate completely, leave the working tree clean and stop. The completion
report must state the decision, branch, commit SHA, pull request, validation
performed, created documents, updated documents, outstanding blockers and
recommended next prompt.

## Acceptance Criteria

List observable acceptance criteria.

Use precise checks:

- endpoints return specific fields;
- clients render specific backend-provided payloads;
- migration preserves expected data;
- stale/unsupported states degrade gracefully;
- diagnostics do not expose secrets.

## Tests

List required tests.

Include where relevant:

- unit tests;
- contract tests;
- integration tests;
- migration tests;
- privacy/redaction tests;
- release or artifact checks;
- client fixture tests.

## Documentation updates

List docs that must be updated in this phase.

Examples:

- `API_CONTRACT.md`
- `TECHNICAL_DESIGN_DECISIONS.md`
- `SYNC_PROMPTS.md`
- `BOOTSTRAP_CODEX_SESSION.md`
- relevant README files;
- foundation docs if a principle changes;
- ADRs if a decision is made.

## Expected commits

Describe the intended commit structure.

Example:

1. domain/storage;
2. resolver/use-case layer;
3. API/contracts;
4. tests;
5. docs.

## Review checklist

- Did the implementation follow the Constitution?
- Did it follow the Domain Model?
- Did it keep personal state on DJConnect Profile?
- Did it keep runtime state on Device?
- Did it keep provider behavior behind Music Backend?
- Did it keep durable intelligence backend-owned?
- Did it keep clients as renderers/control surfaces?
- Did it avoid duplicated contracts?
- Did it avoid duplicated business logic?
- Did it update docs?
- Did it add the right tests?
- Is an ADR needed?

## Merge checklist

- [ ] Branch is based on current target branch.
- [ ] Code compiles locally.
- [ ] Required tests pass locally.
- [ ] CI passes.
- [ ] Docs are updated.
- [ ] Migration and breaking changes are documented.
- [ ] PR is independently mergeable.
- [ ] Next phase can start from the merged result.
