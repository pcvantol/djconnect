# Sharing Experience Architecture

## Status and decision

**Decision:** `SHARING_EXPERIENCE_ARCHITECTURE_ESTABLISHED`

Sharing Experience is a planned, renderer-facing native-client capability that
projects already-authorized DJConnect content into a user-initiated shareable
representation. It is not a DJ Intelligence, Session Runtime, Planner,
Knowledge, DJMoment Engine, Session Flow, Presentation Composer or Broadcast
capability.

This architecture defines no implementation, native share sheet, backend route,
public URL, cloud service or social-network integration.

## Reconciliation matrix

| Existing concept | Owner and lifecycle | Current renderer / maturity | Fit | Sharing boundary |
| --- | --- | --- | --- | --- |
| Track Insight | HA Insight service; current safe track context | Apple, Windows and Pi rich/read-heavy projections; implemented | Extensible | Producer only; it never owns sharing. |
| Immutable DJMoment / Presentation | Runtime and Presentation Composer; immutable active-session contribution | Authorized Renderer Hosts; implemented | Extensible | A current Moment may supply a safe producer projection; sharing does not create or alter a Moment. |
| Session Flow | HA Session Runtime; live, renderer-safe chronological flow | Owner and authorized renderers; implemented | Partially fitting | Only a curated Story may be produced; never the internal Flow, Planner, Runtime or Broadcast event log. |
| Persistent Session / Session Timeline | Session Platform; completed historical record | Owner-authorized history; partial | Extensible | A future Session Summary is distinct from the live Flow. |
| Discover recommendation | HA Discovery service; Profile-scoped result | Rich native clients; implemented | Extensible | Producer may expose only the final recommendation and safe rationale. |
| Ask DJ answer | HA Conversation Platform; Profile-scoped exchange | Rich clients; implemented | Partially fitting | User-selected final renderer-safe answer only; never history, prompt, hidden context or follow-up state. |
| Music DNA | HA Profile Platform; opt-in personal snapshots | Authorized rich-client dashboard; implemented | Partially fitting | Only a future explicit, bounded Summary; never the Profile, raw snapshots or listening history. |
| Broadcast / Presentation | HA Broadcast and Presentation; active-session delivery | Renderer Hosts; implemented | Conflicting as a share model | Remains live renderer delivery only; sharing creates no Broadcast event or realtime path. |
| Profile/Music DNA/Ask DJ export | HA Profile Platform; portable backup envelope | Apple, Windows and HA services; implemented | Conflicting as a share model | Export is private portability and redaction, not social or presentation sharing. |
| Native Share Sheet, share cards, social/deeplinks | Native clients / no canonical contract | Not evidenced in this repository | Missing | Future renderer-local realization only after a bounded implementation increment. |

The discovery records for Apple, Windows and Pi confirm that these clients
render Track Insight, Ask DJ, Music DNA and Discover from server-owned
contracts. They do not establish a canonical share-sheet, share-card, social
or deep-link implementation. Historical use of “share” in profile and history
export is intentionally unrelated.

## Contract and ownership

```text
authorized Share Producer
        -> immutable Share Projection
        -> Native Share Renderer
        -> platform-native Share Sheet
```

A producer supplies only renderer-safe, already-existing content:

- title and bounded body;
- optional image reference already safe for the renderer;
- optional opaque/deferred deep-link target; and
- bounded, non-secret metadata.

The native Share Renderer owns platform format, card/image composition,
localization, native share-sheet invocation and any later platform-specific
format. It does not derive intelligence, modify the projection, fetch private
context, manufacture a Session story, or communicate with another renderer.

The canonical contract is internal and transport-neutral. It is deliberately
not a Home Assistant API, a Broadcast projection, a capability-negotiation
protocol or a public share URL.

## Candidate producers

| Producer | Eligible shareable representation | Required exclusion |
| --- | --- | --- |
| Track Insight | Safe selected track facts and existing artwork reference. | Raw backend payloads, profile inference and credentials. |
| Current DJMoment | One immutable renderer-safe Moment. | Planner rationale, hidden Knowledge inputs and runtime state. |
| Session Flow Story | Curated start, meaningful Moments, Session Updates, Recommendations, end and duration. | Full Flow, technical events, planner state, Broadcast events and provider queue. |
| Session Summary | A completed-session summary, distinct from live Flow. | Live Runtime state and unapproved historical detail. |
| Discover Result | Final recommendation and renderer-safe rationale. | Discover/Planner context and private preference inputs. |
| Ask DJ Answer | User-selected renderer-safe final answer. | Conversation history, prompt, source-private context and pending follow-up state. |
| Music DNA Summary | Explicit future bounded personal summary. | Full Music DNA, listening history, inferred detail and any default disclosure. |

Producer eligibility does not make a producer implemented, force every native
client to support it, or authorize a new producer API. It establishes only a
future assessment boundary.

## Privacy and lifecycle

Sharing is always explicit and user-initiated. It is never automatic, realtime,
background Broadcast, Profile export, support upload or cross-renderer
coordination. A renderer must not share private Profile data, provider
credentials, bearer/OAuth tokens, raw prompts, Ask DJ history, hidden context,
Music DNA details or Session Runtime state.

Each future producer must resolve profile privacy before creating a projection.
A missing authorization or unsupported local renderer means no share action;
there is no fallback to a broader projection. A user choosing the platform
share sheet remains responsible for the receiving destination after the
bounded local representation is handed to the OS.

## Deferred work

The following require independent assessment and implementation: native share
sheet adapters, images/cards, share-action UX, deep-link resolution, a
Session Summary contract, animated/video Stories, carousel formats, community
themes, public landing pages and cloud/social sharing services.

No deferred item authorizes a new Runtime event, Broadcast event, Session Flow
mutation, Planner change or DJMoment Engine change.

## CMB-11 assessment outcome

**Decision:** `GO_SHARING_REFINEMENT_REQUIRED`

Repository evidence confirms that Sharing is a renderer-facing capability, not
a DJ Intelligence capability. Existing Track Insight, one immutable current
DJMoment, curated Session Flow Story, future Session Summary, Discover result
and user-selected Ask DJ answer are producer candidates; each remains owned by
its existing server capability and must expose only a bounded safe result.

An immutable, producer-neutral and renderer-safe Share Projection is the
fitting future contract boundary. It remains separate from native share APIs
and does not need a Broadcast projection: existing Broadcast is live delivery,
not sharing. Apple and Windows are the evidenced native Share Renderer targets;
Browser and future Renderer Hosts require their own local capability evidence.

The remaining gap is not a new Runtime or Broadcast contract. A separately
authorized refinement must select exactly one existing producer and one native
Renderer Host, confirm its local capability inventory and Profile privacy
evidence, then decide whether a bounded Share Projection contract is necessary.

## CMB-11 contract refinement

**Decision:** `GO_ADDITIONAL_REFINEMENT_REQUIRED`

The single reference producer is **Track Insight** (`CAP-IN-01`): it is already
implemented, renderer-safe and exposes selected track facts plus an existing
safe artwork reference without requiring a live Session, Planner context or
personal Discover result. The single reference Native Share Renderer is
**Apple**: repository evidence identifies it as a rich Track Insight renderer;
Windows, Pi, Browser and future hosts are outside this refinement.

The minimal future contract remains immutable and producer-neutral: bounded
title/body, optional renderer-safe image reference and bounded non-secret
metadata. Track Insight owns the safe source result; the Share Contract owns
the immutable projection; the Apple Native Renderer owns local formatting and
the Platform Share API invocation. DJ Intelligence does not invoke platform
sharing. Music DNA, Profile, Performance Memory, Runtime/Planner context,
provider payloads/credentials and Ask DJ history are never payload fields.

Existing renderer-safe Track Insight information can be reused, but it is not
itself a Share Projection. The missing Apple-native share capability inventory
and explicit local privacy/selection evidence prevent authorizing an
implementation or a new projection contract.

## CMB-11 continuation: Apple local boundary

**Decision:** `GO_SHARING_IMPLEMENTATION`

Track Insight selects only its existing renderer-safe result; the Sharing
Contract freezes the bounded payload; the Apple Native Renderer performs local
payload qualification, formatting and Share Sheet invocation; the end user
explicitly selects the share action and Apple Share Sheet destination.

Before opening the Share Sheet, Apple must accept only renderer-safe contract
fields and reject internal metadata, Music DNA, Profile, Performance Memory,
Planner/Runtime context, provider payloads, Ask DJ history, credentials and
tokens. This is a local qualification boundary, not a server policy,
Broadcast or API contract.

Cross-repository evidence is now available in `pcvantol/djconnect-app` PR #50,
commit `5d2723bd8ab5686f99188e715226492fae74d27c`: existing
`TrackInsightShareRenderer`, `TrackInsightShareService` and SwiftUI `ShareLink`
prove local payload rendering, user-initiated selection and platform Share
Sheet invocation. This supports the stated ownership and privacy boundaries;
no objective contract gap remains. A bounded Track Insight-to-Apple Sharing
implementation is authorized, without Runtime, Broadcast, API or DJ
Intelligence changes.
