# Session Intelligence Golden Scenario Catalogue

## Status

**Canonical catalogue, architecture-only.** These scenarios are approved
product behaviors to protect in future automated E2E verification. They do not
implement a Scenario Driver, Session Capture, assertions or CI execution.

## Catalogue rules

Each Golden Scenario protects a user-visible Session Intelligence outcome using
deterministic, provider-independent fixtures. It exercises the canonical
Runtime → Planner → Knowledge → DJ Moment → Session Flow → Broadcast path.
Its capture and assertions observe outcomes only; they never participate in
planning or repair a Session.

Blocking assertions belong to structural invariants or an explicitly approved
deterministic behavior. Non-blocking observations belong to quality reporting
until separately promoted by governance.

The [Session Intelligence Qualification Policy](SESSION_INTELLIGENCE_QUALIFICATION_POLICY.md)
defines how these approved product-behavior contracts participate in Golden
Smoke, Golden Regression and non-blocking Quality Reports.

## SI-GOLDEN-001 — Helpful track context reaches every Session surface

| Field | Contract |
| --- | --- |
| Product intent | A listener receives one helpful, safe DJ contribution when a newly started track has valid context. |
| User story | As a listener, when a Session observes an eligible track, I receive one coherent DJMoment and see the same semantic history across Session Flow and Broadcast. |
| Runtime preconditions | One active ordinary server-owned Session; no prior realization for the deterministic track fixture; eligible Track Started evaluation. |
| Deterministic fixture | Normalized track `Harbor Lights` by `Northline`, valid bounded Track Insight with safe artist or track context, fixed mood/persona and no provider dependency. |
| Event timeline | Start Session → submit one eligible Track Started observation → Runtime plans → Knowledge resolves valid safe context → Moment realizes → Flow/Broadcast publish → stop Session. |
| Expected Planner behavior | Selects one eligible contextual intent through the canonical planning lifecycle; does not make multiple approvals. |
| Expected Knowledge behavior | Selects only the approved safe evidence and produces one valid bounded context. |
| Expected DJMoment behavior | Creates one immutable non-Silence Moment with frozen Presentation Intent and safe references. |
| Expected Session Flow | Contains the one published semantic contribution in server-defined order. |
| Expected Broadcast behavior | Publishes the matching renderer-safe Moment and Flow projection once; no Planner or Knowledge internals appear. |
| Blocking assertions | One canonical approval; exactly one immutable realized Moment; Flow and Broadcast refer to the same result; Session cleanup removes Runtime-scoped state. |
| Non-blocking observations | Moment category distribution, safe-context coverage and optional presentation-length metadata. |
| Forbidden outcomes | Duplicate realization, partial/raw knowledge exposure, browser-derived Flow, provider query, or a second publication pipeline. |

## SI-GOLDEN-002 — Recent repetition gives the listener a different story

| Field | Contract |
| --- | --- |
| Product intent | The DJ avoids immediately repeating the same type of story when another valid context is available. |
| User story | As a listener, after an Artist Story has just played, the next eligible track does not immediately repeat an Artist Story when a valid alternative exists. |
| Runtime preconditions | Active Session with bounded runtime-scoped Performance Memory containing the preceding Artist Story; deterministic valid alternative evidence available. |
| Deterministic fixture | Two distinct normalized tracks; first produces Artist Story, second exposes valid Album or Genre context; fixed Planner influence and ordering. |
| Event timeline | Start Session → first Track Started yields Artist Story → record in Performance Memory/Flow → second Track Started → plan and resolve → publish result → stop. |
| Expected Planner behavior | Deterministically avoids the immediately repeated Artist Story and chooses the valid non-repeating candidate without changing recommendation-spacing authority. |
| Expected Knowledge behavior | Resolves only the newly approved alternative category. |
| Expected DJMoment behavior | Realizes one immutable alternative-category Moment, never retroactively changing the first Moment. |
| Expected Session Flow | Preserves first then second contribution in canonical order. |
| Expected Broadcast behavior | Distributes the two renderer-safe results in Flow order; exposes no Performance Memory internals. |
| Blocking assertions | No immediate repeated Artist Story when the fixture provides a valid alternative; one approval per evaluation; deterministic rerun produces the same semantic result. |
| Non-blocking observations | Repetition ratio and diversity score across the fixture. |
| Forbidden outcomes | Persistent learning, Profile mutation, multiple approvals, changing historical Moments or bypassing existing recommendation spacing. |

## SI-GOLDEN-003 — Missing knowledge never breaks the listening Session

| Field | Contract |
| --- | --- |
| Product intent | A temporary knowledge failure degrades safely without interrupting music or ending the Session. |
| User story | As a listener, if DJ knowledge is unavailable, playback and the active Session continue calmly rather than showing invented information or failing. |
| Runtime preconditions | Active Session, eligible contextual intent and no prior realization for the fixture track. |
| Deterministic fixture | Normalized track with a typed safe knowledge timeout, malformed result, or absent required intent evidence; no live provider. |
| Event timeline | Start Session → eligible Track Started → Planner approves contextual opportunity → Knowledge returns typed unavailable/invalid outcome → Moment fallback → Flow/Broadcast outcome → stop. |
| Expected Planner behavior | Retains its bounded decision and does not fabricate a replacement intent. |
| Expected Knowledge behavior | Rejects invalid/unavailable data without leaking partial context. |
| Expected DJMoment behavior | Creates canonical intentional Silence with a safe reason; Runtime stays active. |
| Expected Session Flow | Records the resulting Silence according to canonical Flow semantics. |
| Expected Broadcast behavior | Does not publish a partial user-visible Moment; any safe Session projection remains coherent. |
| Blocking assertions | Runtime remains active; no invented or partial context; exactly one safe fallback; no duplicate retry loop; cleanup succeeds. |
| Non-blocking observations | Fallback count, typed failure class and Silence ratio. |
| Forbidden outcomes | Session failure, playback mutation, raw exception/provider payload, indefinite retry, or a non-Silence narrative from invalid knowledge. |

## SI-GOLDEN-004 — Replanning stays bounded and preserves approved intent

| Field | Contract |
| --- | --- |
| Product intent | Future planning adapts to changed observable playback without churning what is already approved or inventing future playback. |
| User story | As a listener, when the known upcoming playback changes, the Session adapts predictably while keeping the immediate approved contribution stable. |
| Runtime preconditions | Active Session with Rolling Session Horizon, one approved earliest eligible intent, observable bounded upcoming projection and no provider queue access. |
| Deterministic fixture | Initial two-entry normalized upcoming projection; updated projection first extends, then shortens observable coverage; fixed influence. |
| Event timeline | Build planning window → readiness/approve earliest intent → update projection → replan → equivalent replan → observe planned statuses → stop. |
| Expected Planner behavior | Creates a new generation only for material change, preserves the approved intent, retains valid provisional intents, supersedes obsolete provisional intents and does not recreate consumed slots. |
| Expected Knowledge behavior | Invalidates or preserves prefetch/readiness only through generation and validity rules; consumes no stale preparation. |
| Expected DJMoment behavior | Does not realize future intents merely because they are planned. |
| Expected Session Flow | Remains unchanged by planning-only replanning until an actual approved realization occurs. |
| Expected Broadcast behavior | Exposes no Horizon, planned intent, readiness or prefetch internals. |
| Blocking assertions | Equivalent replan is a no-op; material change is deterministic; approved intent remains singular and stable; obsolete provisional intent is superseded; no fabricated future playback. |
| Non-blocking observations | Generation count, replanning churn and provisional-intent retention ratio. |
| Forbidden outcomes | Multiple approved intents, historical Flow rewrite, future DJMoment realization, provider queue read, persistence or renderer transport exposure. |

## SI-GOLDEN-005 — Repeated Silence triggers one calm Session Update

| Field | Contract |
| --- | --- |
| Product intent | The Session can acknowledge a sustained quiet phase once, rather than repeatedly interrupting or becoming stuck. |
| User story | As a listener, after two intentional Silences, the DJ may issue one coherent resetting Session Update at the next eligible evaluation. |
| Runtime preconditions | Active Session with bounded Performance Memory containing exactly two immediately preceding Silence Moments, valid existing Session Direction context and no recent Session Update guard conflict. |
| Deterministic fixture | Three deterministic Track Started evaluations: two each produce intentional Silence; the third has safe Direction context but no extra audience, provider or Profile input. |
| Event timeline | Start Session → first Silence → second Silence → next eligible Track Started → Planner direction evaluation → Knowledge context → Session Update realization → Flow/Broadcast publish → stop. |
| Expected Planner behavior | Approves at most one resetting Session Update for the documented recent-silence condition; guards prevent direct repetition. |
| Expected Knowledge behavior | Uses only existing safe Session Direction context; no new provider retrieval. |
| Expected DJMoment behavior | Produces one immutable Session Update with frozen Presentation Intent. |
| Expected Session Flow | Preserves the two Silence outcomes followed by the single Session Update in canonical order. |
| Expected Broadcast behavior | Publishes the renderer-safe immutable Session Update through existing Broadcast only. |
| Blocking assertions | Exactly one approved Update; no Update before the stated condition; Update follows the existing Planner/Knowledge/Moment path; prior Moments remain immutable. |
| Non-blocking observations | Silence recovery frequency, Update frequency and interval between update opportunities. |
| Forbidden outcomes | Direct renderer message, multiple Updates for one evaluation, audience inference, playback mutation or rewritten Flow history. |

## SI-GOLDEN-006 — Intentional Silence respects the listener's space

| Field | Contract |
| --- | --- |
| Product intent | The DJ can intentionally choose not to interrupt when the bounded policy says no contribution is appropriate. |
| User story | As a listener in a calm Session, I experience uninterrupted music rather than forced commentary when the current policy prefers Silence. |
| Runtime preconditions | Active Session with a deterministic Silence-capable slot or an approved Silence decision; no unsafe knowledge requirement. |
| Deterministic fixture | Fixed chill/low-interruption influence and observable bounded playback coverage yielding an eligible Silence opportunity. |
| Event timeline | Start Session → submit eligible event/slot → Planner selects Silence → canonical Silence realization → Flow records outcome → safe Broadcast projection behavior → stop. |
| Expected Planner behavior | Selects Silence deterministically under the fixture policy and does not turn it into a missing-data error. |
| Expected Knowledge behavior | Performs no unnecessary knowledge retrieval for intentional Silence. |
| Expected DJMoment behavior | Creates one immutable canonical Silence with an intentional reason and no narrative content. |
| Expected Session Flow | Represents the Silence in canonical semantic history without reordering prior contributions. |
| Expected Broadcast behavior | Does not manufacture a visual DJMoment event; renderer-safe Session state remains coherent. |
| Blocking assertions | Silence is intentional and singular; no provider call or fabricated text; Flow ordering holds; Runtime remains active and cleanup succeeds. |
| Non-blocking observations | Silence ratio, timing position and interruption-avoidance distribution. |
| Forbidden outcomes | Treating Silence as Runtime failure, user-visible invented story, playback mutation, duplicate Silence publication or a browser-owned interpretation. |

## Catalogue evolution

New scenarios must be approved product behaviors, retain this complete contract
shape and identify blocking assertions separately from non-blocking quality
observations. Golden Scenario revisions are versioned and reviewable. They must
prefer semantic and structural evidence over byte-for-byte narrative snapshots
unless a specific narrative contract becomes explicitly deterministic.

## References

- [E2E Verification Architecture](SESSION_INTELLIGENCE_E2E_ARCHITECTURE.md)
- [Session Intelligence Qualification Policy](SESSION_INTELLIGENCE_QUALIFICATION_POLICY.md)
- [Developer Experience Roadmap](../product/DEVELOPER_EXPERIENCE_ROADMAP.md)
- [DJ Moment Engine](../technical/DJ_MOMENT_ENGINE.md)
