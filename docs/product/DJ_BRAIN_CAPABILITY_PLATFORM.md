# DJ Brain Built-in Capability Platform

## Decision

**Decision:** `EXISTING_ARCHITECTURE_EXTENDED_WITH_CAPABILITY_POLICY`

DJConnect has a fixed, internal registry of trusted, repository-owned DJ Brain
capability declarations. It is a selection boundary, not a public plugin
platform or a second intelligence engine.

The canonical execution path remains:

```text
Runtime -> Planner -> Knowledge Engine -> DJMoment Engine -> Session Flow -> Broadcast
```

The registry answers **can** a trusted built-in capability support an intent.
The Profile policy answers **may** it be selected for that Profile. The
existing Planner retains the sole **should** decision. Knowledge, Moment,
Session Flow and Broadcast retain their existing authority after Planner
approval.

## Trusted registry contract

Every declaration is `origin: built_in` and contains a capability id, version,
owner, maturity, stability, supported intents, required inputs, produced
outputs, safety policy, failure semantics, qualification profile and default /
minimal membership. The current declarations cover Track Insight, Artist,
Album, Genre and Recommendation context, Transition, Session Update and
Discover metadata.

The registry does not discover packages, load files, download code, dynamically
import modules, execute extensions, negotiate permissions, expose a public API
or introduce signing, sandboxing, remote registries or client installation.
It is immutable process-local metadata owned by the Home Assistant Runtime.

## Profile-owned policy

The existing Profile Platform store persists exactly one policy with the
Profile and therefore uses no new store, configuration flow or client-facing
setting. Its modes are:

| Mode | Resolution |
| --- | --- |
| `full` | Stable built-ins enabled by default. |
| `minimal` | Fixed stable minimal-membership built-ins only. |
| `custom` | Stable built-ins named by the Profile allowlist. Unknown and partial ids are ignored safely. |

Profile context resolves the policy into eligible Planner intents. Session
creation can pass that resolved immutable set to the existing Runtime. A policy
change replaces only unrealized planning work, invalidates disallowed planned
or approved intents and lets the existing bounded replanning path recompute.
It emits no Session Update, changes no Playback, and does not publish a policy
projection to renderer hosts.

## Failure and qualification semantics

Policy exclusion occurs before Knowledge preparation and DJMoment realization.
When policy leaves no eligible intent, the existing canonical Silence path is
used. No policy condition fabricates knowledge, creates a new DJMoment type,
or weakens existing Knowledge/Moment validation.

The platform changes neither Golden Scenario catalogue nor Smoke/Regression
semantics. Existing Scenario coverage continues to protect the canonical
Runtime lifecycle; focused capability-policy tests protect declaration trust,
policy resolution, persistence and Planner filtering.

## Explicit boundaries

- No Runtime, Planner, Knowledge Engine, DJMoment, Session Flow or Broadcast
  replacement or parallel path.
- No Audience Signals, Lyrics Knowledge, external knowledge source, provider,
  playback or renderer behavior.
- No public, third-party or downloadable capability package model.
- No new CI, verification or governance framework; action pinning and advisory
  semantics are unchanged.

## Deferred work

Profile policy editing UX, remote capability delivery, experimental capability
rollout and any new DJ Intelligence capability require their own bounded
assessment and implementation increments. They are not implied by this
metadata and policy boundary.
