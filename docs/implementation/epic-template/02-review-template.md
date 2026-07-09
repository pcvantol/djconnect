# Phase Architecture Review Template

Use this after every implementation phase before starting the next phase.

## Phase reviewed

- Epic:
- Phase:
- Repositories:
- PRs:
- Date:

## Constitution review

Did the implementation follow `DJCONNECT_CONSTITUTION.md`?

Notes:

## Domain Model review

Did the implementation follow `DOMAIN_MODEL.md`?

Questions:

- Is personal state on DJConnect Profile?
- Is hardware/runtime state on Device?
- Is provider-specific behavior behind Music Backend?
- Is temporary state a Session with expiry?
- Are clients acting as Renderers/Clients?

Notes:

## Responsibility review

Did implementation move responsibilities to the correct repository or layer?

Notes:

## Duplication review

Did the phase introduce duplicated contracts or duplicated business logic?

Notes:

## Documentation review

Were docs updated with the implementation?

Docs changed:

- 

Docs still needed:

- 

## Test review

Were the right tests added or updated?

Tests run:

- 

Missing tests:

- 

## ADR review

Is an ADR needed?

Answer:

If yes, describe:

- decision;
- affected repositories;
- expected ADR number or title.

## Technical debt introduced

List any technical debt introduced intentionally.

Include:

- reason;
- owner;
- follow-up issue/backlog item;
- acceptable lifetime.

## Product debt introduced

List any product debt introduced intentionally.

Include:

- user-facing implication;
- owner;
- follow-up issue/backlog item.

## Security and privacy review

Did the phase preserve privacy and security expectations?

Questions:

- Are tokens and secrets redacted?
- Is personal data scoped correctly?
- Are shared devices protected from personal leakage?
- Are exports/migrations safe?
- Are logs/diagnostics safe?

Notes:

## Next phase readiness

Can the next phase begin?

Answer:

Blocking items:

- 

Recommended next phase adjustments:

- 
