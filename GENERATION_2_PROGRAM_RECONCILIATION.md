# DJConnect Generation 2 Program Reconciliation

**Status:** Canonical program-status record

**Owner:** Platform governance

**Scope:** Documentation and governance reconciliation only. This record changes
no Runtime, renderer, capability, ownership, API, product behaviour, roadmap
priority or implementation commitment.

## Purpose

Generation 2 now has a completed architectural and product-direction baseline.
This record distinguishes that baseline from current Product Development and
future Platform Evolution. It is the canonical reconciliation companion to
`ROADMAP_INDEX.md`; the program registers remain `PRODUCT_ROADMAP.md`,
`PLATFORM_EVOLUTION_BACKLOG.md` and the Innovation Lab records.

## Status vocabulary

Every current program register uses exactly one of these statuses:

| Status | Meaning |
| --- | --- |
| Completed | Delivered canonical foundation, decision or bounded increment. |
| Current execution | The one presently authorized program workstream. |
| Planned | Approved future work that still needs its own assessment and increment. |
| Deferred | Deliberately not current; prerequisite evidence, policy or authorization is absent. |
| Historical | Retained evidence of a prior transition, release or planning state. |
| Retired | Deliberately superseded with no active delivery path. |

## Generation 2 program status

## Generation 2 execution model

Generation 2 is product-led. The current **Product Initiative** is
**Reference Experience**: create the first complete, canonical DJConnect
experience across bounded interaction and presentation surfaces.

```text
Product Initiative: Reference Experience
        ↓
Engineering execution: Automated Session Intelligence E2E Verification
```

Automated Session Intelligence E2E Verification remains the current
engineering execution. It enables the Reference Experience through trustworthy
existing Session behaviour; it is not a replacement for the product direction.

The public Community release defines the minimum lovable DJConnect product,
not the complete long-term product vision.

The roadmap governs product evolution. Platform implementations support that
product; they do not automatically determine product readiness.

### Completed foundations

| Foundation | Status | Canonical authority |
| --- | --- | --- |
| Product Definition 2.1 | Completed | `docs/product/PRODUCT_DEFINITION.md` |
| Product Philosophy Alignment | Completed | `docs/product/` and PR #436 evidence |
| Capability Architecture | Completed | `DJCONNECT_CAPABILITY_MODEL.md` |
| Host Role Architecture | Completed | `HOST_ROLE_ARCHITECTURE.md` |
| Raspberry Pi Platform Foundation | Completed | `RASPBERRY_PI_PLATFORM_FOUNDATION.md` |
| Experience Foundation v1 | Completed | `EXPERIENCE_FOUNDATION.md` |

These foundations are durable direction, not active roadmap work. Their future
changes require an evidence-backed assessment rather than a parity or
implementation assumption.

### Current execution

| Program | Item | Status | Canonical record |
| --- | --- | --- | --- |
| DJConnect Product Development | Automated Session Intelligence E2E Verification | Current execution | `docs/product/DEVELOPER_EXPERIENCE_ROADMAP.md` |

### Product-maturity phase navigation

`PRODUCT_ROADMAP.md` is the sole detailed phase register. This reconciliation
records only its program-level status:

| Phase | Product maturity | Status |
| --- | --- | --- |
| 0 | Generation 2 Foundations | Completed |
| 1 | Reference Experience | Current execution |
| 2 | Apple Premium Experience | Planned |
| 3 | Public Release Readiness Assessment | Planned |
| 4 | Productization | Planned |
| 5 | Community Public Release | Planned |
| 7 | Personal AI DJ evolution | Deferred |
| 8 | Future Cloud evolution | Deferred |

Phase 3 may conclude that planned capabilities, including Session Timeline or
minimal Music DNA work, are unnecessary for the first public release. It
authorizes no implementation. Productization does not automatically include
Personal capabilities or commit a paid model. Commercial readiness is
assessment-only and may conclude that the first public release remains
Community-only.

Productization covers release preparation rather than product-scope expansion:
distribution and beta strategy, App Store readiness, supported-platform and
accessibility review, signing/notarization/CI/CD readiness, compliance,
support operations, release notes and localization approval. Each workstream
still requires its own selection and implementation authorization.

### Runtime Readiness

**Runtime Readiness** is the minimum functional completeness required before
Community Public Release. It is a release gate owned by Home Assistant, the
sole Runtime Host. It determines whether the Community product promise can be
fulfilled, independently of any one renderer implementation.

Its release evidence covers the existing Runtime and its canonical contracts:
Session Runtime, Planner, Knowledge, DJMoment, Presentation, Broadcast, Ask
DJ, Track Insight, Discover, Session Memory, capability contracts, pairing and
APNs support where required for Apple. This is a readiness classification, not
a new capability or implementation commitment.

For every capability that needs a renderer, Release Readiness Assessment first
decides whether it is **Community-defining** or **Platform-extending**.
Community-defining capability is Runtime Readiness work because it is required
for the Community promise. Platform-extending capability belongs to Platform
Adoption because it broadens reach without changing that promise. Renderer
implementation alone never determines placement.

### Platform Adoption

**Platform Adoption** is the independent, non-release-gating stream that
brings the completed Runtime to additional Concrete Hosts when doing so does
not block the current product milestone. It includes Raspberry Pi, ESPHome
Voice, the Desktop Platform Family, Website, Universal Receiver renderer and
ESP32 adoption work. It changes neither Runtime ownership nor product
readiness.

Apple remains the first public consumer product and the premium reference
implementation of the Community product; it never owns the product or the
Runtime. Desktop adoption follows the first public Apple release. Future Linux
remains separately assessable, with no technology choice made here.

### VibeCast Release Readiness decision

VibeCast is not pre-classified. The Release Readiness Assessment asks whether
Community v4.0 fulfils its product promise without VibeCast. If yes, VibeCast
remains Platform Adoption work. If no, it becomes Runtime Readiness work
through the Universal Receiver renderer. The assessment, not a renderer
implementation, determines that outcome.

Future user-facing work follows the Experience Engineering sequence:

```text
Experience Assessment
        ↓
Experience Gap Analysis
        ↓
Implementation
        ↓
Experience Validation
```

This sequence consumes `EXPERIENCE_FOUNDATION.md`; it does not duplicate it.

### Future evolution

Platform Evolution retains assessment-first foundation evolution, governance,
qualification, privacy, release maturity and capability-profile follow-up
(including CMB-05 through CMB-10). It is not the primary source of
user-facing roadmap progress.

## Historical reconciliation

`DJCONNECT_V4_COMPLETION_ROADMAP.md` is a **Historical** engineering record.
It documents the transition to the completed Session Intelligence Runtime and
the former V4 completion framing. It remains valuable evidence, but no longer
sets active Generation 2 execution or architecture-creation priority.

Pre-Generation 2 roadmap material retained below the active table in
`PRODUCT_ROADMAP.md` is likewise **Historical** product and release memory. It
does not create active scope, sequencing, pricing or platform commitments.

## Program structure

```text
Generation 2 Foundations (Completed)
        ↓
Generation 2 Product Development (Current execution)
        ↓
Future Platform Evolution and Innovation (Planned or Deferred)
```

## Recommended next Product Development slice

Continue the existing Automated Session Intelligence E2E Verification work as
the enabling engineering stream for Phase 1, Reference Experience. Any
subsequent user-facing slice must begin with the applicable capability
assessment and Experience Gap Analysis; it must not reopen completed
foundations or assume cross-host capability parity.

## Reconciliation outcome

- Completed foundations are recognized consistently as completed.
- Active product work is separated from architecture creation and historical
  transition records.
- Platform Evolution contains future, assessment-first work only.
- No Runtime, product, capability, ownership, API or implementation decision
  is changed by this reconciliation.

## Review disposition

### Updated planning records

- `ROADMAP_INDEX.md`
- `PRODUCT_ROADMAP.md`
- `PLATFORM_EVOLUTION_BACKLOG.md`
- `CAPABILITY_MODEL_BACKLOG.md`
- `DJCONNECT_V4_COMPLETION_ROADMAP.md`
- `ENGINEERING_PROGRAM_MODEL.md`
- `MANAGEMENT_SUMMARY.md`

### Reviewed without change

- `docs/product/PRODUCT_DEFINITION.md` — remains the canonical product
  philosophy.
- `DJCONNECT_CAPABILITY_MODEL.md` — remains the completed Capability
  Architecture authority.
- `HOST_ROLE_ARCHITECTURE.md` — remains the completed Host Role authority.
- `RASPBERRY_PI_PLATFORM_FOUNDATION.md` — remains the completed Pi Platform
  Foundation authority.
- `EXPERIENCE_FOUNDATION.md` — remains the completed Experience Engineering
  baseline and gap-analysis authority.

### Duplicated concepts reduced to references

The Product Roadmap and Platform Evolution Backlog no longer carry an active
architecture-foundation program. They reference the completed foundation
authorities instead. The V4 document retains transition evidence only and
defers active execution to the current Product Roadmap and this reconciliation
record.
