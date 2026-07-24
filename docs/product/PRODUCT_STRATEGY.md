# DJConnect Product Strategy

Status: foundation established  
Repository: `pcvantol/djconnect`

## Purpose

This document defines the canonical Product Strategy foundation for DJConnect.
It applies the product philosophy in
[`PRODUCT_DEFINITION.md`](PRODUCT_DEFINITION.md); Product Definition 2.1 is
the authority for the AI DJ identity, the DJ Session as the product, and the
Community/Personal proposition.

It is intentionally concise. It does not define features, epics, stories,
priorities, implementation phases or release scope.

## Mission

DJConnect is a local-first AI DJ that helps people experience music through
one coherent DJ Session: calm control, useful intelligence and shared presence
across the devices already around them.

## Vision

DJConnect should become the local-first AI DJ that feels personal without
becoming intrusive, expressive without becoming noisy and coherent across
multiple interaction and presentation surfaces without making any surface
responsible for backend intelligence.

## Product Principles

- The DJ Session is the product; individual capabilities contribute to that
  coherent experience.
- The AI DJ is the product identity; music playback remains owned by the
  configured Music Backend.
- Music should remain the center of the experience and control should feel
  immediate, physical and low-friction.
- Intelligence should explain, recommend and assist without pretending to know
  more than the available evidence supports.
- Personalization must respect profile, household, guest and private-session
  boundaries.
- Shared-room experiences should be useful without leaking personal history.
- Clients should render and control; the backend should own durable
  intelligence.
- Community must remain a complete, valuable local-first AI DJ experience
  without a DJConnect account; it is never a trial or an upgrade funnel.
- Personal is the same AI DJ becoming more personal through opt-in Music DNA,
  never a separate product or a different DJ.
- Cloud and premium capabilities should extend the same AI DJ rather than
  replace the local-first foundation.

## Target Users

DJConnect is built for:

- Home Assistant users who want natural music control at home;
- music listeners who want useful context, recommendations and DJ-style
  assistance without opening a phone for every action;
- households that need shared music experiences without personal data leakage;
- builders and early adopters who value local-first hardware and client
  interoperability;
- future product users who may want richer intelligence, presentation and
  cloud-assisted experiences after the platform baseline is certified.

## Long-Term Product Direction

DJConnect's validated product direction is one cross-surface, local-first AI
DJ experience, with Home Assistant as its local-first foundation.

The product should grow around:

- one coherent DJ Session across eligible interaction and presentation surfaces;
- AI DJ intelligence that enriches playback without owning it;
- profile-aware personalization and privacy;
- shared-room and household experiences;
- physical, voice and rich-client control surfaces;
- presentation surfaces that make music context feel alive;
- optional cloud or premium extensions that preserve the local-first core.

## Relationship With Platform Strategy

Platform Strategy owns the current engineering transition toward a verified
Platform Baseline v1.0.

Product Strategy is subordinate to that platform state. Platform Baseline v1.0
is certified; Generation 2 Product Development is now the primary engineering
program inside the frozen platform architecture.

## Relationship With Innovation Labs

Innovation Labs are the canonical source for product ideas.

Product Strategy accepts only validated concepts. It must not duplicate the
Innovation Lab, and it must not convert unvalidated ideas into commitments.

## Relationship With Product Roadmap

`PRODUCT_ROADMAP.md` is the canonical Generation 2 Product Development
roadmap. It owns strategic sequencing, not raw ideas or implementation tasks.
Its retained pre-Generation 2 material is historical memory only.

## Relationship With Product Backlog

Product work enters an implementation backlog only after roadmap selection and
the applicable discovery/architecture phase. `PRODUCT_ROADMAP.md` remains the
single product-direction record until a later approved decomposition creates a
separate product backlog.
