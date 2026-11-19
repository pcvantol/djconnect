# R0 — Runtime Independence Research

Status: Research.
Priority: Strategic.
Scheduling: Not scheduled.
Decision status: No architectural decision has been made.

This document is a strategic research whitepaper for DJConnect runtime
evolution. It is not an implementation Epic, not a roadmap commitment and not a
proposal to leave Home Assistant.

Home Assistant remains the primary DJConnect runtime.

Epic 3 established a runtime-independent identity model. Future runtime
evolution can build on the Profile Platform without redesigning identity. No
runtime changes are recommended before Epic 4.

## 1. Current Situation

DJConnect currently uses this architecture:

```text
Clients
  -> Home Assistant Runtime
  -> DJConnect Integration
  -> Music Backend
```

The canonical backend runtime is the Home Assistant custom integration in
`pcvantol/djconnect`. Clients such as iOS, macOS, watchOS, Windows, Raspberry
Pi and ESP32 consume backend-owned capabilities through Home Assistant HTTP,
websocket, services, entities and device/runtime state.

Home Assistant provides the local runtime, configuration model, integration
host, storage, device registry, entity model, Assist, services, event bus,
automation engine and access to Music Assistant and other ecosystem
integrations. DJConnect adds product-specific Profile identity, device
pairing, music backend routing, Ask DJ orchestration, Music DNA, Track Insight,
Discovery and client contracts on top of that runtime.

Strengths:

- local-first operation;
- strong privacy posture;
- mature device and entity infrastructure;
- established integration ecosystem;
- Home Assistant Assist and TTS/STT integration;
- Music Assistant interoperability;
- open-source community trust;
- a developer-friendly place to validate product architecture.

Limitations:

- Home Assistant installation is a prerequisite;
- mainstream users may not understand the runtime dependency;
- setup can involve Docker, networking, accounts, URLs and configuration;
- mobile-first users expect app-led onboarding;
- support questions can be about Home Assistant rather than DJConnect.

## 2. Strategic Question

The research question is:

Should Home Assistant always be the required DJConnect runtime, or should Home
Assistant eventually become one possible runtime?

No decision has been made.

This document explores whether DJConnect could support additional runtimes over
the next 3-10 years while preserving one platform architecture, one domain
model and one product identity.

## 3. Why Home Assistant Is Valuable

DJConnect started on Home Assistant for strong architectural reasons.

Home Assistant is local-first by design. That matches DJConnect's Community
promise: music intelligence, voice/Assist integration and household device
control should work without forcing every user into a cloud product.

Home Assistant also provides:

- mature config flows and options flows;
- a stable device registry and entity registry;
- an event bus and automation engine;
- service calls and websocket/HTTP APIs;
- Home Assistant Assist for voice pipelines;
- TTS/STT integrations;
- Music Assistant and media ecosystem access;
- secrets and storage conventions;
- diagnostics and Repairs patterns;
- a community that understands local automation.

This foundation lets DJConnect focus on product-specific architecture: Profile,
Device, Household, Music Backend, Music Account, Playback Zone, Resolver,
Insight and client rendering contracts. It avoids building a full runtime
before the product architecture is proven.

## 4. Current Limitations

Home Assistant is also DJConnect's largest mainstream adoption barrier.

Many users simply expect:

- install an app;
- sign in or pair;
- select music services;
- start using the product.

Home Assistant can require:

- choosing installation hardware;
- understanding Docker or supervised installs;
- network discovery and local URLs;
- Home Assistant user accounts;
- integration configuration;
- OAuth redirect URL setup;
- possible YAML exposure;
- restarts and logs;
- domain knowledge that non-technical users do not have.

This creates support burden. A DJConnect onboarding problem may really be a Home
Assistant installation, networking, Docker, TLS, Nabu Casa or router problem.

It also shapes perception. A consumer music companion that requires a home
automation platform may feel too technical for App Store-style adoption, even
when the product experience itself is polished.

## 5. Potential Runtime Evolution Scenarios

These scenarios are research options. They are not mutually exclusive and none
is selected.

### Scenario A — Home Assistant Only

DJConnect remains a Home Assistant-native platform.

Advantages:

- strongest local-first alignment;
- lowest runtime fragmentation;
- simplest backend ownership model;
- best fit for open-source Community;
- least duplicate infrastructure.

Disadvantages:

- Home Assistant remains mandatory;
- consumer adoption remains constrained;
- onboarding support continues to include Home Assistant;
- App Store-style expectations are harder to meet.

Engineering effort: Low to moderate.
Maintenance: Lowest.
Community impact: Strong continuity.
Business impact: Slower mainstream growth, strong open-source credibility.

### Scenario B — Hosted Home Assistant

DJConnect provides or partners around one managed Home Assistant instance per
customer.

Advantages:

- preserves Home Assistant runtime semantics;
- reduces user installation burden;
- keeps compatibility with Home Assistant integrations;
- could create a managed subscription path.

Disadvantages:

- operationally complex;
- Home Assistant hosting may conflict with user expectations about local-first;
- per-customer environments are expensive to run and support;
- upstream Home Assistant changes still matter.

Engineering effort: High.
Maintenance: High.
Community impact: Potentially positive if Community remains first-class.
Business impact: Possible managed revenue, significant support cost.

### Scenario C — DJConnect Runtime

DJConnect creates a standalone lightweight runtime, for example Python,
FastAPI, SQLite and embedded services.

Advantages:

- app-led onboarding becomes possible;
- runtime can be tailored to DJConnect's domain;
- less Home Assistant knowledge required;
- deployable on desktop, NAS, Pi, mini PC or appliance.

Disadvantages:

- duplicates many Home Assistant capabilities;
- requires new storage, auth, config, services, scheduling and integration
  systems;
- risks weakening Home Assistant Community focus;
- requires a strong plugin/integration model for music and smart home features.

Engineering effort: Very high.
Maintenance: Very high.
Community impact: Risk of confusion unless HA remains first-class.
Business impact: Larger market potential, much larger product/support burden.

### Scenario D — Plugin-Based Runtime

DJConnect Core becomes runtime-independent and delegates runtime-specific
behavior through adapters:

```text
DJConnect Core
  -> Runtime Adapter
    -> Home Assistant
    -> Standalone Runtime
    -> Cloud Runtime
```

Advantages:

- preserves one domain model;
- allows Home Assistant to stay the primary adapter;
- creates a path to standalone or cloud experiments;
- makes runtime dependencies explicit.

Disadvantages:

- requires careful boundaries;
- adapter contracts can become complex;
- test matrix expands;
- bad abstractions could slow all development.

Engineering effort: High.
Maintenance: Moderate to high.
Community impact: Good if Home Assistant adapter remains canonical.
Business impact: Strategic flexibility.

### Scenario E — Cloud-Hosted Runtime

DJConnect offers a multi-tenant cloud runtime for profile sync, push, LLM
orchestration, premium voice features and portability.

Advantages:

- best fit for mainstream mobile onboarding;
- can support Personal and future Cloud features;
- central push and entitlement systems become easier;
- cross-install Profile sync becomes natural.

Disadvantages:

- cloud costs;
- privacy/compliance burden;
- security attack surface;
- risk of undermining local-first Community;
- internet dependency for some experiences.

Engineering effort: Very high.
Maintenance: Very high.
Community impact: Sensitive. Must not replace local-first Community.
Business impact: Strong commercial potential, high operational responsibility.

### Scenario F — Installer

DJConnect provides a one-click Mac, Windows or Linux installer that runs the
needed local runtime.

Advantages:

- reduces installation complexity;
- keeps local-first possible;
- aligns with consumer expectations better than manual Home Assistant setup;
- could bundle a standalone runtime or guided Home Assistant deployment.

Disadvantages:

- packaging complexity across platforms;
- updates, firewall, permissions and background services become support topics;
- still needs a runtime architecture underneath.

Engineering effort: High.
Maintenance: High.
Community impact: Helpful if it can also install/connect to Home Assistant.
Business impact: Strong adoption lever.

### Scenario G — Embedded Appliance

DJConnect ships or documents a dedicated appliance: mini PC, Raspberry Pi, NAS
package or DJConnect-branded hardware.

Advantages:

- controlled runtime environment;
- simpler support than arbitrary user installs;
- can preserve local-first architecture;
- attractive for households that want a device, not a platform project.

Disadvantages:

- hardware lifecycle and supply chain;
- OS updates and security patching;
- distribution and support logistics;
- may create expectations of a turnkey consumer product.

Engineering effort: Moderate to high.
Maintenance: High.
Community impact: Positive if open and optional.
Business impact: Hardware/service opportunity with operational complexity.

## 6. Home Assistant Dependency Matrix

| Capability | Required today | Can be replaced? | Replacement complexity | Strategic importance |
| --- | --- | --- | --- | --- |
| Config Flow | Yes | Yes | Medium | High |
| Options Flow | Yes | Yes | Medium | High |
| Storage | Yes | Yes | Medium | Critical |
| Entity Registry | Yes | Partially | High | High for HA, lower outside HA |
| Area Registry | Useful | Yes | Medium | Medium |
| Device Registry | Yes | Yes | High | High |
| Services | Yes | Yes | Medium | High |
| Event Bus | Yes | Yes | Medium | Medium |
| Conversation | Yes | Yes | High | High |
| Assist | Yes | Partially | High | High |
| Music Assistant | Optional but valuable | Partially | High | High for local music |
| Automation Engine | Valuable | Partially | Very high | High for HA users |
| Websocket | Yes | Yes | Medium | High |
| HTTP | Yes | Yes | Low to medium | Critical |
| LLM integration | Indirect | Yes | High | High |
| Notifications | Yes for push paths | Yes | Medium | High |
| Scheduling | Yes | Yes | Low to medium | Medium |
| State Machine | Yes | Partially | Very high | High for HA |
| Secrets | Yes | Yes | Medium | Critical |

## 7. Possible DJConnect Core

A future runtime-independent architecture could look like:

```text
Clients
  -> DJConnect Core
  -> Runtime Adapter
    -> Home Assistant
    -> Standalone Runtime
    -> Cloud Runtime
```

DJConnect Core would own runtime-neutral concepts:

- Profile;
- Household;
- Device;
- Music Backend abstraction;
- Music Account routing;
- Playback Zone;
- Resolver;
- Ask DJ orchestration contracts;
- Insight contracts;
- privacy policy;
- export/import formats;
- client capability contracts.

Runtime adapters would own host-specific integration:

- Home Assistant config/options flows;
- HA services, entities, registries and Assist;
- standalone app configuration;
- cloud auth and tenancy;
- runtime-specific storage and scheduling.

Core should stay runtime-independent only if the boundaries remain clean. If the
abstraction makes the Home Assistant integration worse, the architecture has
failed.

## 8. Plugin Architecture

Runtime-specific functionality could eventually become plugins.

Examples:

- Home Assistant Plugin;
- Automation Plugin;
- Voice Plugin;
- Music Backend Plugin;
- Notification Plugin;
- Cloud Plugin.

A plugin model could help separate capabilities from runtime assumptions. For
example, the Home Assistant Plugin could implement entity registry, services,
Assist and HA storage, while a standalone runtime could implement local HTTP,
SQLite and simple scheduling.

Risks:

- too many plugin contracts too early;
- version compatibility problems;
- unclear ownership;
- hard-to-debug cross-plugin behavior;
- plugin system becoming more complex than the product.

Plugin architecture should not be pursued until DJConnect Core boundaries are
stable through later intelligence and capability epics.

## 9. Migration Strategy

If runtime independence is ever pursued, it should happen without splitting the
platform.

Principles:

- Home Assistant remains first-class;
- Community remains local-first and open-source;
- core domain contracts remain shared;
- client contracts remain runtime-neutral;
- runtime adapters must conform to the same capability matrix;
- exports/imports remain non-secret by default;
- no client should need separate product logic per runtime.

Possible migration path:

1. Keep Home Assistant as canonical runtime.
2. Extract only runtime-neutral services when a real second runtime exists.
3. Define adapter interfaces from proven code, not speculation.
4. Add contract tests that every runtime adapter must pass.
5. Keep Home Assistant users receiving every architectural improvement.
6. Use profile export/import as the portability bridge before cloud sync.

## 10. Business Considerations

Community:

- strongest when Home Assistant remains local-first and fully capable;
- benefits from open contracts and no forced cloud dependency.

Personal:

- may benefit from easier onboarding, profile portability and optional managed
  services;
- should not remove Community capabilities.

Future Cloud:

- could support push, profile sync, hosted AI, premium voices, entitlements and
  remote convenience;
- creates privacy, security, cost and compliance obligations.

Open source:

- Home Assistant runtime preserves credibility and contribution pathways;
- standalone or cloud runtimes need clear license and governance decisions.

Commercial opportunities:

- managed runtime;
- appliance;
- Personal tier;
- hosted intelligence;
- support subscriptions.

Support cost:

- Home Assistant support burden is high for mainstream users;
- standalone/cloud support burden is high in different ways;
- multi-runtime support is highest unless contracts and diagnostics are strong.

Developer productivity:

- one runtime is fastest;
- multiple runtimes require adapter contracts, fixtures and CI;
- runtime independence should wait until architecture stability justifies it.

User adoption:

- app-led onboarding and managed runtimes may unlock mainstream adoption;
- Home Assistant remains attractive for technically confident local-first users.

## 11. Risks

Key risks:

- platform fragmentation;
- multiple runtimes drifting apart;
- plugin compatibility problems;
- larger test matrix;
- increased support burden;
- community confusion about what DJConnect is;
- cloud costs and operational risk;
- privacy mistakes in sync/export/import;
- security vulnerabilities in new auth/storage layers;
- weakening the Home Assistant integration by abstracting too early.

The largest architectural risk is premature abstraction. DJConnect should not
invent a runtime-independent core until the current Home Assistant architecture
has matured enough to reveal stable boundaries.

## 12. Conclusions

This research makes no implementation recommendation.

It creates no roadmap commitment.

It does not decide whether DJConnect should remain Home Assistant-only or
eventually support additional runtimes.

The balanced conclusion is:

- Home Assistant is currently the correct primary runtime.
- Home Assistant is a major strength and a real adoption barrier.
- Runtime independence may become strategically valuable.
- Epic 3 established a runtime-independent identity model through the Profile
  Platform.
- Future runtime evolution can build on Profile, Request Context and the
  Profile Resolver without redesigning identity.
- No runtime changes are recommended before Epic 4.
- The platform should avoid premature abstraction.
- Any future runtime evolution must preserve one domain model, one capability
  contract and first-class Home Assistant support.

This topic should be revisited after:

- Epic 3: Profile Architecture;
- Epic 4: Intelligence Platform;
- Epic 5: Feature Flags and Experimental Framework.

At that point, DJConnect should have enough mature architecture to judge whether
runtime independence is an opportunity, a distraction or a necessary evolution.
