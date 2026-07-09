# Repository Discovery Report: `pcvantol/djconnect-app`

## Overview

The Apple repo owns native iOS, iPadOS, macOS and watchOS Intelligence Client UX. It is the richest client surface and currently the functional reference for Windows.

## Purpose

Owns Apple-native rendering, pairing UX, Ask DJ UI, Music DNA UI, Discover, Track Insight rendering, VibeCast control/render affordances, APNs client registration and Watch proxy behavior.

Does not own backend intelligence, Music DNA storage, Spotify OAuth secrets, central relay behavior or canonical platform truth.

## Strengths

- Strong alignment with backend-owned intelligence: README explicitly says HA owns Ask DJ interpretation, follow-up state and playback execution.
- Rich contract fixture tests for Music DNA, Music Discovery, websocket capabilities and recent-played rendering.
- Watch proxy model preserves `client_type:"watchos"` while using iPhone transport.
- CI covers Swift tests, HTTP/WebSocket fixture checks, localization, unsigned builds and release publication paths.
- Good privacy posture around app-private token storage and redacted diagnostics.

## Weaknesses

- AGENTS references only a small subset of the new foundation docs; it should point to `FOUNDATION_INDEX.md` and the full foundation set.
- Repo-local `SYNC_PROMPTS.md` exists, which conflicts with the foundation rule that cross-repo sync prompts should remain canonical in HA.
- Dirty local worktree observed during audit; not a platform defect, but it raises discovery reproducibility risk.
- "DJConnectKeychain.swift" filename remains despite app-private storage. The README explains it, but it remains a cognitive smell.

## Architecture observations

Apple is broadly correct as an Intelligence Client. It renders backend-provided state and actions rather than owning intelligence. It is ahead of other clients on Personal-facing surfaces, but that also creates product gravity: future platform work must avoid letting Apple UX become de facto canonical architecture.

## Product observations

The Apple app matches the Product Vision better than most repos: it presents Ask DJ, Music DNA, Discover, Track Insight and VibeCast as one rich experience. Local bonus games are explicitly local-only and do not pollute backend logic, but they are product-adjacent and should remain optional.

## Technical debt

- Foundation references need refresh.
- Repo-local sync prompt should be removed or reduced to a pointer.
- Derived-data directories are abundant locally and can obscure audits.
- TestFlight/App Store distribution remains a dedicated workstream.

## Product debt

- Apple is ahead of Windows/Pi; parity expectations need to be explicit so Apple does not define unreviewed product behavior.
- Personal/Community entitlement boundaries are UI-visible but not platform-final until Profile Architecture exists.

## Feature drift

Ahead: VibeCast, Discover, Music DNA, rich Ask DJ, Watch support.  
Behind or constrained: background audio and foreground wake phrase remain research/gated.

## CI observations

Strong but macOS runner dependent. Release workflows are mature but complex.

## Security observations

Good APNs/bootstrap documentation. Ensure no APNs provider credentials or issuer secrets enter client code. Local token storage posture is strong.

## Privacy observations

Strong on diagnostics and local cache boundaries. Profile privacy remains dependent on HA Epic 3.

## Recommendations

1. Refresh AGENTS to point to `FOUNDATION_INDEX.md`, `PLATFORM_PRINCIPLES.md`, `REPOSITORY_OWNERSHIP.md` and ADRs.
2. Replace repo-local `SYNC_PROMPTS.md` with a pointer to canonical HA docs.
3. Create a client capability parity checklist comparing Apple, Windows and Pi.
4. Keep Apple as UX reference, not architecture source of truth.

## Priority

P1 for foundation sync and sync-prompt cleanup; P2 for parity checklist.

## Estimated effort

Small to medium.

## Scores

| Dimension | Score |
| --- | ---: |
| Product | 9 |
| Architecture | 8 |
| Documentation | 8 |
| Testing | 8 |
| CI/CD | 8 |
| Security | 8 |
| Privacy | 8 |
| Release | 8 |
| Developer Experience | 7 |
| Overall | 8.0 |
