# Prompt History: Session Continuation Capability Family

**Generation and engineering program:** Generation 2, Phase 1 — DJ Intelligence
Evolution / Product Development
**Engineering mode:** Product & Platform Architecture
**Branch:** `codex/register-session-continuation`
**Decision:** `GO_SESSION_CONTINUATION_REGISTERED`
**Execution date:** 2026-07-26
**Scope:** future capability-family registration only; no assessment,
implementation, notification, push, APNs, Runtime, Planner, DJMoment,
Renderer, preference, deep-link or Music Backend change.

## Archived prompt

Register **Session Continuation** as a future Product Development capability:
an invitation to return to an existing active DJ Session only when a relevant
DJMoment or interaction is ready. It is not a push capability, a marketing or
engagement mechanism, a request to start a new Session, or a playback action.
It remains assessment-first and outside the current Execution Horizon.

Record the distinct conceptual chain:

```text
Active DJ Session -> Planner-relevant DJMoment -> Continuation Opportunity
-> Continuation Policy -> privacy-safe Notification Projection
-> Platform Notification Renderer -> existing active Session
```

The Planner owns relevance only. A future Opportunity is temporary and
session-scoped but is not automatically a notification. A future Policy owns
the external interruption and delivery decision, including future evidence for
validity, user activity, consent, preferences, quiet hours, privacy,
authorization and bounded frequency. Renderer Hosts own only native
presentation; Apple/APNs is transport, not the capability owner. Home
Assistant Runtime retains active-Session state and the Music Backend retains
all playback ownership.

Require a minimal, category-only external projection: no full DJMoment, quiz
content, stories, media/provider references, playback command, credential,
Profile, Runtime identity, Planner/Knowledge context, Music DNA, Ask DJ
content, Session Direction, queue or listening history. On open, future
delivery must revalidate the Session, opportunity, authorization, Moment
currentness/consumption and host eligibility; expiry routes safely to the
current Session or neutral state without stale content or hidden fallback.

Keep Session Continuation independent of Interactive DJMoments: the latter is
participation inside an active Session, while the former is a potential return
invitation. Either interactive or non-interactive existing/future DJMoments may
later provide an opportunity. Do not create a parent-child dependency.

Future assessment may cover opportunity and policy boundaries, consent,
frequency, projection privacy, safe persona/Mood catalogue, deep linking,
expiry/revalidation, Apple/APNs renderer evidence, shared profiles,
content-free observability and release/privacy qualification. Any delivery is
separately authorized. Do not change the current Execution Horizon or
prioritize this registration over existing work.

## Validation and limitations

- Repository synchronization, objective PR #508 merge/containment verification
  and current development-host qualification completed before this record.
- No Session Continuation capability was found in the canonical roadmap,
  Capability Model, documentation, implementation or tests. Existing
  Interactive DJMoments, Native Surface Integration and APNs/push records have
  distinct ownership and were not extended as parallel models.
- Validation is documentation-only: roadmap consistency and `git diff --check`
  apply. No notification, APNs, Runtime, Planner, Renderer, API or product
  validation is implied.

## Recommended next prompt

Resume the canonical Execution Horizon. Consider a Session Continuation
Capability Assessment only after a later explicit authorization and its
recorded active-Session, privacy, authorization and renderer evidence.
