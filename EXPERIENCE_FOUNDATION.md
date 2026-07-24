# DJConnect Experience Foundation v1

**Status:** Canonical reverse-engineered baseline

**Owner:** DJConnect Experience Engineering

**Scope:** The cross-surface experience of DJConnect. This document is
documentation-only: it changes no capability, Runtime, renderer, ownership,
API contract, product scope, roadmap sequence or implementation commitment.

## Purpose and authority

Experience Engineering is a first-class engineering discipline. It defines how
DJConnect feels, communicates, expresses personality and becomes recognizable
across interaction and presentation surfaces.

```text
Capability Engineering
        ↓
Product Engineering
        ↓
Experience Engineering
```

Capability Engineering defines what is possible; Product Engineering defines
the coherent AI DJ and DJ Session value; Experience Engineering defines how
that product is perceived. Experience Engineering owns none of the
capabilities, Runtime, platform architecture or implementation technology.

This Foundation is the canonical authority for experience intent. Current
implementations are evidence, not authority. Version 1 records a
reverse-engineered baseline; it does not certify any implementation as the
final DJConnect experience or prescribe a Design System, UI specification or
Figma implementation.

Product Definition 2.1 remains authoritative for product philosophy. The
Capability Model, Host Role Architecture and Raspberry Pi Platform Foundation
remain authoritative for capability and platform participation.

## Evidence reviewed

The following current user-facing evidence was reviewed without modifying it:

| Surface | Evidence reviewed | Baseline observation |
| --- | --- | --- |
| Apple macOS and iPhone/iPad | `djconnect-app` SwiftUI root, launch and Track Insight presentation sources | Dark navy/purple cards, blue-to-lilac gradients, rounded continuous surfaces, native navigation and sheets. |
| Apple Watch | `DJConnectWatchRootView` | A compact native navigation stack, purple/blue accents, sheets and optional haptics. |
| Raspberry Pi native appliance | `djconnect-pi` QML `Main.qml`, controls and `MoodTheme.js` | Full-screen, mood-aware gradients, large touch controls, local overlays and intentional appliance states. |
| Raspberry Pi web portal | `web_portal.py` | Dark radial background, elevated panels, large gradient controls and prominent toast feedback. |
| Universal Receiver | `universal_receiver.html` | Deliberately plain, readable HTML: current playback, Current DJ Moment and Session Flow as functional projection evidence. |
| Website | `djconnect-website` public pages | Dark gradient marketing surfaces, blurred/translucent navigation, rounded cards and experience-led AI DJ language. |

The Universal Receiver is a functional renderer foundation, not evidence of a
finished visual identity. Website marketing pages are evidence of public brand
expression, not automatically a native-client specification.

## Reverse-engineered experience inventory

### Visual language

The strongest repeated visual signal is a dark, nocturnal canvas with blue,
violet, magenta and occasional cyan or green light. Apple and Pi use layered
gradients for controls, artwork fallbacks and elevated panels. The website
uses radial and linear gradients, translucent/blurred navigation and rounded
card-like surfaces. Pi adds visible elevation through shadows and borders.

Observed density varies by context: Apple rich surfaces use generous padding
and cards; Pi prioritizes large touch targets and high-at-a-distance legibility;
the Receiver prioritizes readable semantic projection over visual treatment.

### Motion language

Observed motion is bounded and purpose-led: Pi portal toasts fade/translate,
Pi controls alter opacity while pressed, and native Apple surfaces use platform
transitions, navigation and sheets. The Watch adds optional haptic feedback.
The available evidence does not establish one shared timing, easing, reveal or
particle language. Ambient particle behavior is product direction in VibeCast,
not a current cross-surface baseline.

### Colour language

Blue-to-purple gradients are the most repeated accent. Pi explicitly maps
gradient, focus and toast colors to Session Mood values; its observed palette
includes cool blue/lilac, teal/lilac, green/yellow/orange and pink/purple/yellow
families. Apple repeats blue/lilac/purple accents. Website pages add cyan,
green and violet against deep navy.

Warning, failure and success colors are locally expressed (for example Pi
portal warning/danger controls and status chips). A shared semantic-color
contract is not established by the evidence.

### Typography and information density

The observed typography is bold, high-contrast and hierarchical: large track
titles and controls on Pi; readable card, list and detail hierarchy on Apple;
compact glanceable presentation on Watch; system/sans-serif readability on web
surfaces. Secondary information is consistently muted. Apple, Watch and Pi
use platform-appropriate density rather than one fixed layout density.

### Interaction language

Current interactions use direct controls for playback, output and bounded
actions; native navigation for richer exploration; sheets/dialogs for welcome,
permissions, confirmation and opt-in; and toast-like transient feedback where
available. Ask DJ is conversation-oriented on eligible rich surfaces and is
bounded by confirmations/actions rather than a free-form control substitute.

The Pi appliance explicitly uses local screen-off, temporary-wake and return-to-
now behaviour. The Receiver intentionally exposes no rich interaction pattern
beyond its projection role. There is no evidence for a single cross-surface
navigation, bottom-sheet or loading pattern.

### Presentation language

Current presentation centres on current playback, artwork, progress, a Current
DJ Moment/Track Insight contribution and chronological Session Flow where the
surface supports it. Pi pairs those with mood-aware visual context; Apple
offers richer personal detail; Watch compresses the same product vocabulary;
the Receiver proves a readable renderer-safe projection; VibeCast remains a
future ambient experience rather than current implementation evidence.

### Tone of voice and iconography

Current language consistently uses DJConnect, Ask DJ, Track Insight, Discover,
Music DNA, Current DJ Moment and Session Flow. Public language leads with the
AI DJ, listening, understanding and shared presence; it does not lead with a
music provider or Home Assistant dashboard. Existing localized labels and
copy remain the authority; this Foundation does not rewrite them.

Apple uses platform-native SF-symbol-style iconography; Pi uses familiar
playback symbols and text-backed controls; website uses restrained inline SVG
and simple icon motifs. Weight, fill/outline treatment and semantic mapping are
not yet consistent enough to be normative.

## Recognizable DJConnect identity

The present evidence makes DJConnect recognizable through the combination of:

- a calm, night-time music atmosphere rather than a utilitarian dashboard;
- luminous blue/violet/magenta accents over dark surfaces;
- music as a hosted DJ Session, not merely playback controls;
- concise, helpful DJ vocabulary such as Ask DJ and Track Insight; and
- visual richness that adapts to the attention and privacy of the surface.

These are experience observations, not mandatory implementation tokens.

## Experience assessment

A **Strong** baseline indicates consistent current evidence, not final design
quality or Experience Qualification.

| Category | Maturity | Evidence-led assessment |
| --- | --- | --- |
| Visual language | Strong | Dark, elevated blue/violet gradient language repeats across Apple, Pi and public web. |
| Motion language | Inconsistent | Local transitions, toast motion and haptics exist; no shared observed motion vocabulary. |
| Colour language | Strong | Repeated dark/accent palette; Pi has explicit mood-aware mapping. |
| Typography | Current baseline | Clear hierarchy and muted secondary text recur, with deliberate platform density differences. |
| Interaction language | Inconsistent | Native sheets/navigation and Pi appliance behaviour are strong locally; Receiver is intentionally minimal. |
| Presentation language | Current baseline | Playback, Current DJ Moment, Track Insight and Session Flow recur where appropriate. |
| Tone of voice | Strong | AI DJ, Ask DJ and music-understanding terminology aligns with Product Definition 2.1. |
| Iconography | Inconsistent | Platform-native and web/Pi symbols are useful but lack one evidenced shared language. |
| Identity | Current baseline | The atmosphere and AI-DJ framing are recognizable, but not yet evidenced as uniform on every renderer. |
| Accessibility and loading feedback | Unknown | Local support exists, but no cross-surface experience evidence or qualification baseline was reviewed. |

## Identified inconsistencies and intentional absences

- The Universal Receiver's plain functional treatment does not share the
  visual richness of Apple, Pi or public web; this is recorded, not normalized.
- Pi has explicit mood-aware color mapping; equivalent cross-surface mapping is
  not established by the reviewed Apple and Receiver evidence.
- Motion, icon weight, transient feedback, navigation and loading behavior vary
  by platform and have no canonical cross-surface expression yet.
- Rich Ask DJ, queue browsing, artwork and history are intentionally absent on
  constrained, ambient or receiver contexts where their Capability Model
  projection does not permit them. Absence is not an experience defect.
- VibeCast, ambient particles and rich shared-room presentation remain future
  product direction, not evidence of a current qualified baseline.

## Experience Gap Analysis framework

Every future Product Development increment that changes a user-facing surface
must record this assessment before implementation:

### Current Experience

Describe what a user actually experiences today on each affected eligible
surface. Cite implementation evidence or state `Unknown`; do not infer parity.

### Target Experience

Describe the intended user perception in terms of the current Experience
Foundation and Product Definition—not technology, component names or a copied
implementation from another platform.

### Experience Gap

Classify the evidenced difference as one or more of visual, interaction,
motion, presentation, tone, terminology, accessibility, delight, continuity,
shared-room or personal behaviour. Identify intentional absence separately.

### Experience Decisions

Answer: **Why does this feel like DJConnect?** Record explicit design decisions
and any approved divergence. Do not answer only how it is implemented.

### Experience Validation

State how the resulting experience will be compared with the current
Experience Foundation: appropriate visual, interaction, accessibility, copy or
cross-surface evidence. This creates no automated test or qualification process
by itself.

## Evolution and qualification

```text
Experience Foundation v1
        ↓
Experience Gap Analysis
        ↓
Explicit design decisions
        ↓
Experience Foundation v2
        ↓
Future intentional evolution
```

The Foundation changes only through explicit, reviewable decisions. Historical
implementation drift never changes it automatically.

**Experience Qualified** is a future designation for a renderer that conforms
to the then-current Experience Foundation. It is intentionally only a concept
in v1. It is independent of Platform Qualification and Capability
Qualification; no process, score, gate or certification is introduced here.

## Boundaries and next work

This Foundation does not redesign a UI, prescribe a component library, define
tokens, select technology, change Product Definition, amend Capability
Architecture or approve a renderer implementation. Future work must use the
Gap Analysis framework, make explicit design decisions and then revise the
Foundation deliberately.
