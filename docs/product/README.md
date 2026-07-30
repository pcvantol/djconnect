# DJConnect Product Foundation

Status: foundation established  
Repository: `pcvantol/djconnect`

## Purpose

This directory owns the canonical Product Strategy and Product Definition
foundation for DJConnect. [Product Definition 2.1](PRODUCT_DEFINITION.md) is
the canonical product philosophy: DJConnect is a local-first AI DJ, and one
coherent DJ Session is its primary product experience.

Product Strategy begins where Innovation Labs end. Innovation Labs own ideas,
experiments and open product questions. Product Strategy owns validated product
direction.

This directory does not own implementation planning. The canonical product
roadmap is `../../PRODUCT_ROADMAP.md`; `../../PRODUCT_BACKLOG.md` records only
work selected from that roadmap.

## Ownership Model

The product lifecycle is intentionally separated:

```text
Idea
  -> Innovation Lab
  -> Validated Concept
  -> Product Strategy
  -> Product Roadmap
  -> Product Backlog
  -> Discovery
  -> Architecture
  -> Implementation
  -> Verification
  -> Release
```

Each stage owns different information:

| Stage | Owns | Does not own |
| --- | --- | --- |
| Innovation Labs | Ideas, experiments, open questions, rejected concepts. | Product commitments, sequencing or engineering work. |
| Product Strategy | Validated product direction, principles and long-term product posture. | Feature lists, epics, stories or priorities. |
| Product Roadmap | Strategic sequencing after product learning is mature enough. | Raw ideas or engineering task breakdown. |
| Product Backlog | Engineering work selected from the roadmap. | Product strategy or experimental idea capture. |

## Relationship With Platform Strategy

`PLATFORM_STRATEGY.md` owns why the engineering platform is evolving toward a
verified baseline before business-first engineering.

Product Strategy owns what kind of product DJConnect should become once product
learning is validated enough to guide business-first work.

Product Strategy must fit inside Platform Strategy. It must not redefine
platform architecture, verification governance, repository ownership or release
rules.

## Relationship With Innovation Labs

`INNOVATION_LAB.md` remains the canonical home for product ideas and
experiments.

Ideas do not move into Product Strategy just because they are interesting.
They move only after validation shows they represent durable product direction.

## Relationship With Product Roadmap

`PRODUCT_ROADMAP.md` is the formal Generation 2 Product Development roadmap.
It owns strategic sequencing and must not become an idea dump or engineering
backlog. Retained pre-Generation 2 roadmap content is historical memory only.

## Relationship With Product Backlog

The Product Backlog records selected work after Product Roadmap selection and
approved discovery/architecture work. It owns selected engineering work, not
product strategy. Planned and deferred roadmap work stays outside the backlog
until separately selected.

## Current Documents

- `PRODUCT_PHILOSOPHY_ALIGNMENT_REPORT.md`
- `PRODUCT_STRATEGY.md`
- `PRODUCT_DEFINITION.md`
- `DJ_SESSION_DOMAIN_MODEL.md`
- `CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md`
- `LIVE_PLAYBACK_OBSERVATION.md`
- `DJ_INTELLIGENCE_ARCHITECTURE.md`
- `KNOWLEDGE_SOURCE_ARCHITECTURE.md`
- `DJ_INTELLIGENCE_MATURITY.md`
- `DJ_PRESENTATION_ARCHITECTURE.md`
- `PRESENTATION_COMPOSER_ARCHITECTURE.md`
- `AUDIENCE_EXPERIENCE_ARCHITECTURE.md`
- `DJ_INTELLIGENCE_CAPABILITY_REVIEW.md` — repository-grounded discovery
  inventory of current DJ Intelligence, its bounded planning horizon, knowledge
  sources and documented gaps. This is planning evidence, not a capability or
  implementation authorization.
- `VIBECAST_ARCHITECTURE.md`
- `DJ_SESSION_VISION.md`
- `../../DJCONNECT_V4_ARCHITECTURE.md`
