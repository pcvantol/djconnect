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
