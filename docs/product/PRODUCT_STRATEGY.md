# DJConnect Product Strategy

Status: foundation established  
Repository: `pcvantol/djconnect`

## Purpose

This document defines the canonical Product Strategy foundation for DJConnect.

It is intentionally concise. It does not define features, epics, stories,
priorities, implementation phases or release scope.

## Mission

DJConnect helps people experience music through calm control, useful
intelligence and shared presence across the devices already around them.

## Vision

DJConnect should become a local-first music intelligence product that feels
personal without becoming intrusive, expressive without becoming noisy and
cross-platform without making every client responsible for backend
intelligence.

## Product Principles

- Music should remain the center of the experience.
- Control should feel immediate, physical and low-friction.
- Intelligence should explain, recommend and assist without pretending to know
  more than the available evidence supports.
- Personalization must respect profile, household, guest and private-session
  boundaries.
- Shared-room experiences should be useful without leaking personal history.
- Clients should render and control; the backend should own durable
  intelligence.
- Local-first use must remain complete enough to be valuable without a
  DJConnect account.
- Cloud and premium capabilities should extend the product rather than replace
  the local foundation.

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

DJConnect's validated product direction is a cross-platform music intelligence
layer with Home Assistant as the first local-first runtime.

The product should grow around:

- backend-owned music intelligence;
- profile-aware personalization and privacy;
- shared-room and household experiences;
- physical, voice and rich-client control surfaces;
- presentation surfaces that make music context feel alive;
- optional cloud or premium extensions that preserve the local-first core.

## Relationship With Platform Strategy

Platform Strategy owns the current engineering transition toward a verified
Platform Baseline v1.0.

Product Strategy is subordinate to that platform state. Business-first product
engineering must not begin until Platform Baseline v1.0 is certified.

## Relationship With Innovation Labs

Innovation Labs are the canonical source for product ideas.

Product Strategy accepts only validated concepts. It must not duplicate the
Innovation Lab, and it must not convert unvalidated ideas into commitments.

## Relationship With Future Product Roadmap

The formal Product Roadmap stage does not yet exist under this Product Strategy
foundation.

It will be introduced after Platform Baseline v1.0 has been certified and real
product learning begins. The future Product Roadmap will own strategic
sequencing, not raw ideas or implementation tasks.

The existing top-level `PRODUCT_ROADMAP.md` remains pre-baseline product and
release memory until a future product-roadmap phase explicitly formalizes or
replaces it.

## Relationship With Future Product Backlog

The Product Backlog does not yet exist.

It will be introduced only after the Product Roadmap has selected direction and
engineering work is ready to enter discovery, architecture, implementation,
verification and release.
