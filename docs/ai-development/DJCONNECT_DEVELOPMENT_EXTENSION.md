# DJConnect development extension

This is the locally authored companion to the generated AI-development
projection. It does not replace the eight generic contracts. It records only
development semantics that exist because this repository is the canonical
DJConnect platform foundation and Home Assistant integration.

## Local orientation and durable records

Use `BOOTSTRAP.md` as the local entrypoint. Current engineering truth is in
`REPOSITORY_STATUS.md`, `ENGINEERING_STATUS.md`, `MANAGEMENT_SUMMARY.md`,
`ROADMAP_INDEX.md` and `PROMPT_INDEX.md`. The DJConnect architecture and
product authority starts with `FOUNDATION_INDEX.md`, `PLATFORM_STRATEGY.md`,
`PRODUCT_ROADMAP.md`, `docs/technical/` and the applicable verification
documents. Immutable Prompt History is retained in `docs/history/prompts/` and
is never amended to rewrite an earlier freeze point.

DJConnect's local administrative state vocabulary includes
`REVIEWABLE_FROZEN`, `MERGED_UNRECONCILED`, `MERGED_RECONCILED` and
`WORKSPACE_READY`. A verified merged predecessor may require the dedicated
local Finalization record reconciliation before a later DJConnect production
increment. These terms describe DJConnect records and must not be generalized
as a replacement for the projected contracts.

## DJConnect product and qualification boundary

DJConnect remains authoritative for its Home Assistant integration, AI DJ and
runtime architecture, profiles/session/runtime semantics, Knowledge Engine,
DJ Moment Engine, Session Flow, renderer/client behavior, Pi/QML behavior,
Universal Receiver/VibeCast, Music DNA, Discover, device/client behavior,
roadmap, maturity model, release/runtime rules and Golden/product scenarios.
Those are product semantics and remain in their canonical local architecture,
product and verification documents.

DJConnect qualification is repository-specific. Use the existing Home
Assistant integration tests, static/security checks, Golden Scenario and
product qualification where applicable, plus `git diff --check`. A Verification
or Session Intelligence change records its Golden Scenario relationship; an
indirect relationship needs explicit architectural justification and
proportionate evidence. Repository-specific GitHub policy, required checks,
rulesets, action pinning, secret scanning and release controls remain local
repository state rather than generic prose.

## TDE consumer boundary

The projection owns generic TDE integration. DJConnect owns only its TDE
evidence profile, qualification invocation and references. Technical Debt
Engine architecture, implementation, evidence semantics, security and release
behavior remain owned by `pcvantol/technical-debt-engine`; DJConnect must not
independently author those product semantics.

## Historical Engineering Platform boundary

The Engineering Platform extraction, retired central-store migration,
Operations Console, watcher, Local API, LEGACY/CENTRAL material and immutable
run evidence in `docs/engineering/`, `docs/development/` and
`docs/adr/0019-0026-*` are historical/provenance material unless a document
explicitly states a current DJConnect product requirement. They are retained
for audit and must not be mistaken for live generic AI-development authority.
The current known development-host drift is not a generic contract. Any
task-specific admission exception bypasses only the specified host-readiness
gate, never Git, PR, semantic-equivalence, validation, security or governance.
