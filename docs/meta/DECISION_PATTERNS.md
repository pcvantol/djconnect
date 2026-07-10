# Decision Patterns

**Status:** Canonical Engineering Guidance

**Audience:** Architects, engineers, reviewers and AI agents

**Scope:** Entire DJConnect platform

---

# Purpose

Not every discovery belongs in the same place.

One of the most common causes of repository entropy is placing information in the
wrong document.

This document describes how engineering decisions are classified.

The objective is consistency.

Every significant discovery should have one obvious destination.

---

# Core Principle

Every engineering decision should have exactly one canonical home.

Avoid:

- duplicated knowledge;
- competing sources of truth;
- undocumented decisions;
- hidden assumptions.

---

# Decision Flow

Whenever something new is discovered, first classify it.

```
Discovery

↓

Classification

↓

Canonical Destination

↓

Implementation

↓

Verification

↓

Repository Update
```

Classification comes before implementation.

---

# Foundation

Update the Foundation when the discovery changes the long-term platform.

Examples:

- terminology;
- architecture principles;
- platform philosophy;
- governance;
- ownership;
- domain model.

Foundation documents change rarely.

Foundation should remain stable.

---

# Architectural Decision Record (ADR)

Create an ADR when multiple reasonable architectural options exist.

Use an ADR when:

- alternatives were considered;
- trade-offs exist;
- future engineers need historical context.

Do not create ADRs for routine implementation details.

---

# Platform Baseline

Update the Platform Baseline when a major architectural milestone has been
accepted.

Examples:

- Profile Platform
- Runtime Independence
- Cloud Platform
- Verification Platform

Baselines capture accepted architecture.

Not implementation details.

---

# Technical Design

Update Technical Design when implementation reality changes.

Examples:

- new HTTP routes;
- WebSocket behaviour;
- pairing implementation;
- runtime flows;
- storage;
- logging;
- deployment.

Technical Design documents reality.

Not aspiration.

---

# Verification

Update Verification when expected behaviour changes.

Examples:

- new Scenario;
- new Verification Matrix;
- new Verification Data;
- new Verification Mode;
- new Policy;
- new Planning behaviour.

Verification defines expected behaviour.

Not implementation.

---

# Repository Documentation

Update documentation when developer understanding should improve.

Examples:

- setup;
- workflows;
- development;
- deployment;
- troubleshooting.

Documentation explains.

It does not define architecture.

---

# Meta Engineering

Update Meta documents when engineering practice changes.

Examples:

- collaboration model;
- engineering workflow;
- architectural heuristics;
- lessons learned;
- AI guidance.

Meta documents describe how engineering is performed.

Not how DJConnect behaves.

---

# Innovation Lab

Use Innovation Lab when:

- exploring ideas;
- researching alternatives;
- evaluating future concepts;
- testing feasibility.

Innovation documents are intentionally experimental.

They are not commitments.

---

# Platform Backlog

Create or update backlog items when work remains.

A backlog item should describe:

- remaining work;
- owner;
- priority;
- rationale;
- blocking status.

Do not use backlog items as architecture.

---

# Lessons Learned

Record a lesson when the engineering process itself improved.

Examples:

- repository-first context;
- thin adapters;
- execution environment;
- evidence-first verification.

Lessons should be general enough to help future work.

---

# Completion Reports

Every completed phase should create a Completion Report.

It should answer:

- What changed?
- Why?
- How was it verified?
- What remains?
- What is the next phase?

Completion reports describe a phase.

They do not replace architecture.

---

# Prompt Library

Prompts belong in the Prompt Library.

Prompts are execution instructions.

They should never become the canonical description of architecture.

Architecture belongs in documentation.

Prompts reference documentation.

Not the other way around.

---

# Decision Matrix

| Discovery | Canonical Destination |
|-----------|-----------------------|
| Product philosophy | Foundation |
| Architecture trade-off | ADR |
| Accepted architecture | Platform Baseline |
| Runtime behaviour | Technical Design |
| Expected behaviour | Verification |
| Remaining work | Platform Backlog |
| Research | Innovation Lab |
| Engineering process | Meta Engineering |
| Phase result | Completion Report |
| Execution instructions | Prompt Library |

Every significant discovery should fit one primary category.

Avoid duplicate documentation.

---

# Escalation Rules

When uncertain:

1.

Does this change platform philosophy?

→ Foundation

2.

Does this change architecture?

→ ADR or Platform Baseline

3.

Does this describe reality?

→ Technical Design

4.

Does this describe expected behaviour?

→ Verification

5.

Does this describe engineering practice?

→ Meta Engineering

6.

Does work remain?

→ Backlog

7.

Is the idea experimental?

→ Innovation Lab

---

# Closing Principle

The repository becomes easier to navigate when every decision has one obvious
home.

Good engineering is not only about making good decisions.

It is also about placing those decisions where future engineers immediately know
where to find them.
