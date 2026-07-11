# DJConnect Product Foundation

Status: foundation established  
Repository: `pcvantol/djconnect`

## Purpose

This directory owns the canonical Product Strategy foundation for DJConnect.

Product Strategy begins where Innovation Labs end. Innovation Labs own ideas,
experiments and open product questions. Product Strategy owns validated product
direction.

This directory does not own implementation planning.

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

## Relationship With Future Product Roadmap

A formal Product Roadmap stage under this Product Strategy does not yet exist.

The existing top-level `PRODUCT_ROADMAP.md` remains pre-baseline product and
release memory until a future post-baseline product-roadmap phase explicitly
formalizes or replaces it.

The future Product Roadmap will own strategic sequencing. It should not become
an idea dump or engineering backlog.

## Relationship With Future Product Backlog

The Product Backlog does not yet exist.

It should be introduced only after Platform Baseline v1.0 has been certified,
real product learning begins and the Product Roadmap has selected strategic
direction. The Product Backlog will own selected engineering work, not product
strategy.

## Current Documents

- `PRODUCT_STRATEGY.md`
