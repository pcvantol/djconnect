# Knowledge Source Architecture

**Status:** Canonical conceptual architecture
**Owner:** DJConnect Product Development
**Scope:** Provider-independent knowledge qualification and normalization for
the existing V4 Knowledge Engine. This document introduces no provider,
Runtime behaviour, API, cache implementation or Lyrics capability.

## Purpose

DJConnect enriches an active Session with safe, relevant knowledge without
coupling the Runtime to a music, editorial, lyrics or AI provider. This
architecture defines the internal boundary between an external source and the
existing Knowledge Engine.

It preserves the established V4 ownership model:

- the **Session Planner** decides whether and when knowledge is needed;
- the **Knowledge Engine** acquires and assembles eligible knowledge;
- the **DJ Moment Engine** performs storytelling from an approved context;
- **Broadcast** distributes immutable Moments; and
- **Renderer Hosts** present them without resolving knowledge themselves.

## Canonical path

Source qualification is governance outside the active Runtime. Resolution is
performed only for an approved Knowledge Intent inside the existing Knowledge
Engine.

```text
Source Contract and Source Qualification     outside Runtime
                    ↓
Planner-approved Knowledge Intent            Session Runtime
                    ↓
Knowledge Resolver                           Knowledge Engine
                    ↓
Qualified Knowledge Object                   Knowledge Engine internal
                    ↓
Knowledge Context                            Runtime-scoped Engine output
                    ↓
DJ Moment Engine → immutable DJMoment → Broadcast → Renderer Hosts
```

No source is ingested merely because it is available. A resolver may use an
existing prepared result only when it exactly matches the approved intent and
the Runtime's existing prepared-knowledge rules.

## Source Contract and Knowledge Qualification

A **Source Contract** determines whether a source category or concrete source
is eligible for a stated DJConnect use before Runtime use is possible. It
records the permitted subject matter, source category, provenance standard,
quality expectation, licensing and rights basis, provider-terms reference,
attribution, retention, allowed processing, and permitted presentation scope.

**Knowledge Qualification** is the per-resolution decision that a normalized
object produced under an eligible Source Contract is usable for this Knowledge
Intent. It verifies identity, provenance, content category, quality,
freshness, confidence, privacy, rights metadata and the requested Moment,
Broadcast and renderer scopes.

They are intentionally separate:

| Concern | Question | Owner |
| --- | --- | --- |
| Source Contract | May this source be used for this class of DJConnect knowledge? | Platform governance and source policy |
| Knowledge Qualification | May this resolved object enter this approved Runtime decision? | Knowledge Engine |

An object with absent, expired, conflicting or insufficient qualification is
not eligible. The Knowledge Engine returns bounded empty context; existing
Silence handling remains the safe outcome.

## Knowledge Resolver

The **Knowledge Resolver** is an internal responsibility of the existing
Knowledge Engine, not a new Runtime service or public API. It owns:

- provider communication and authentication;
- raw payload reception, validation and disposal;
- provider-to-canonical normalization;
- provenance, source category, freshness, confidence and quality evaluation;
- rights and attribution metadata; and
- contract-bound cache access and invalidation.

It never generates a DJMoment, schedules a Moment, exposes a provider schema,
participates in Broadcast or bypasses Knowledge Qualification. Raw provider
payloads terminate at this boundary. No Runtime component, Moment Engine,
Broadcast consumer or Renderer Host receives them.

## Knowledge Object

A **Knowledge Object** is one provider-independent, source-qualified internal
representation of knowledge about an identified subject. It is neither a
provider payload nor an API, Broadcast, renderer, cache or persistence format.

`knowledge_content` is the canonical term for its normalized substantive
material. It is preferred to *claim*: an object can carry a fact,
classification, relationship or bounded context without asserting that every
kind of knowledge is a single proposition.

Every object conceptually includes:

```text
subject_identity                 knowledge_domain
knowledge_type                   knowledge_content
provenance                       source_category
source_contract                  confidence
quality_status                   freshness
rights_basis                     provider_terms_reference
attribution_requirement          retention_class
allowed_processing               broadcast_scope
renderer_scope                   allowed_djmoment_types
storytelling_value
```

The model is conceptual: an implementation may choose an internal structure
only when a separately approved capability needs it. It must preserve these
semantics without exposing provider-specific fields outside the Resolver.

### Knowledge Type taxonomy

The canonical provider-independent types are:

| Type | Meaning |
| --- | --- |
| `FACT` | Bounded verifiable information about a subject. |
| `INSIGHT` | Qualified explanatory or interpretive context. |
| `CLASSIFICATION` | A bounded categorization, such as genre or production characteristic. |
| `RELATIONSHIP` | A qualified link between identified subjects. |
| `TIMELINE_EVENT` | A dated or ordered historical occurrence. |
| `STATISTIC` | A scoped measured value with method and freshness. |
| `CONTEXT` | Bounded situational context that does not fit another type. |
| `RECOMMENDATION` | A source-qualified candidate or reason; never a playback command. |

No additional canonical type is currently justified. Rights-Controlled
Expression is a domain with stricter eligibility, not a type that bypasses
qualification.

### Knowledge Domain taxonomy

| Domain | Scope |
| --- | --- |
| Music Context | Track, artist, album, genre, release, credit and identifier context. |
| Artist Context | Artist-specific facts and qualified context. |
| Album Context | Release and album-specific facts and qualified context. |
| Production Context | Production, studio, influence or technique context. |
| Historical Context | Timeline, award, chart or cultural-history context. |
| Relationship Context | Collaboration, influence and related-work context. |
| Recommendation Context | Qualified discovery and similarity context. |
| Session Context | Runtime-owned current Session, Flow and Moment context; not external. |
| Performance Context | Runtime-owned ephemeral repetition and pacing evidence; not external. |
| Profile Context | Profile-owned Music DNA and preferences; privacy-scoped. |
| Rights-Controlled Expression | Lyrics, excerpts, editorial text, protected imagery or similar material. |

Domains classify knowledge independently of a provider. Session, Performance
and Profile Context retain their existing owners and do not become externally
resolved knowledge merely because the Knowledge Engine may assemble permitted
context from them.

### Storytelling Value

**Storytelling Value** is a qualitative, source-independent assessment of how
useful a qualified object is for a DJMoment. It is separate from confidence,
correctness, freshness and rights eligibility. A highly confident fact can have
low storytelling value; a valuable object still fails qualification when its
rights or freshness are insufficient.

The Planner may later use Storytelling Value only when selecting between
equally valid Knowledge Context. This document introduces no Planner policy or
selection behaviour.

## Knowledge Context

A **Knowledge Context** is a bounded Runtime-scoped assembly of qualified
Knowledge Objects for exactly one approved Knowledge Intent. It is not a
provider response, cache, persistence format or generic source record.

The Knowledge Engine selects only the minimum eligible objects relevant to the
intent, applies privacy and scope filtering, and passes that context to the DJ
Moment Engine. The Engine never receives Resolver responses or raw objects
that failed qualification.

## Cache ownership and retention

All source cache ownership belongs to the Knowledge Resolver. The Knowledge
Engine owns the eligibility decision; the Planner, Moment Engine, Broadcast
and Renderers do not own a source cache.

| Layer | Owner | Content and limit |
| --- | --- | --- |
| Request Buffer | Resolver | Raw response only while required to validate and normalize; dispose immediately afterwards. |
| Resolver Cache | Resolver | Contract-qualified normalized retrieval material; TTL, invalidation and storage follow the Source Contract. |
| Prepared Knowledge | Existing Runtime/Knowledge Engine boundary | Exact approved future intent result only; Runtime-scoped and invalidated on mismatch. |
| Session Cache | Resolver under Runtime scope | Eligible normalized objects only; expires with session or earlier contract limit. |
| Persistent Cache | Separately governed persistence boundary | Never implicit; only explicitly persistence-safe, source-qualified material. |

No cache is authorization to persist provider payloads, rights-controlled
expression or private Profile context. Local-first deployment changes data
location, not the Source Contract or retention restriction.

## Rights, attribution and scope

Every Runtime-eligible Knowledge Object carries `rights_basis`,
`provider_terms_reference`, `attribution_requirement`,
`allowed_processing` and `retention_class`. These fields are mandatory
qualification inputs, not documentation-only annotations.

`allowed_processing` controls, at minimum, whether the object may be used for
context assembly, AI-assisted realization, temporary caching, persistent
storage, voice, Broadcast or a particular renderer scope. A provider or source
may be eligible for one of these uses and ineligible for another.

Rights-Controlled Expression, including future Lyrics Knowledge, remains
ineligible unless its separate approved source and content-governance contract
authorizes the exact retrieval, processing, retention, attribution and
presentation use. This architecture neither authorizes nor implements it.

## DJMoment and Broadcast boundary

Knowledge Objects remain Runtime-internal:

```text
Knowledge Objects → Knowledge Context → DJMoment → Broadcast
```

The DJ Moment Engine consumes only Knowledge Context. It may retain safe source
references required for attribution or auditability in its immutable output,
but never a raw object or provider payload. Broadcast distributes DJMoments and
approved renderer-safe projections, never Knowledge Objects. Renderer Hosts
present approved output and required attribution; they never resolve sources or
invent knowledge.

## Extensibility and exclusions

Story, production, trivia, artist, historical, educational, concert, awards
and future qualified Lyrics capabilities can reuse the same path by adding a
Source Contract and domain-appropriate qualification. They do not require a
provider-specific Runtime, Broadcast route or renderer model.

This document does not select a provider, introduce a provider integration,
change Track Insight, alter Planner behaviour, create a cache, or advance
Lyrics Knowledge.
