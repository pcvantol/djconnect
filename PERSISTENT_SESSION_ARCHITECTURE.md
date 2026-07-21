# Persistent Session Architecture

**Status:** Accepted architecture amendment
**Owner:** DJConnect Product Development
**Scope:** Durable DJ Session domain truth and its boundary with an ephemeral
Session Runtime. This amendment authorizes no storage, migration, recovery,
voice or renderer implementation.

## Decision

A **DJ Session** is a persistent, Profile-owned lifecycle aggregate. A
**DJ Session Runtime** is one ephemeral server-side execution of that Session.
The Runtime is never serialized, backed up as executable state, or restored as
a Python object.

```text
Household
  -> Profile
    -> persistent DJ Session
      -> ephemeral DJ Session Runtime
        -> ephemeral Broadcast and delivery recovery infrastructure
        -> Renderer Hosts
```

The persistent Session is the durable record of the listening experience. The
Runtime owns only its live orchestration. A completed or interrupted Session
remains available as authorized history; a destroyed Runtime does not.

This amendment changes neither the current in-memory Runtime behaviour nor the
current recovery contract. Until a separately authorized implementation exists,
all active Runtimes remain ephemeral and a Home Assistant restart ends their
live execution.

## Ownership

| Owner | Owns | Never owns |
| --- | --- | --- |
| Profile | Session ownership, privacy defaults, retention eligibility and authorization root. | Another Profile's personal history. |
| Persistent Session | Lifecycle, immutable identity, durable Session metadata and historical renderer-safe projections. | Playback control, credentials or Runtime objects. |
| Session Runtime | One live execution, Planner working state, Performance Memory, active Flow and orchestration. | Durable Session truth or restart restoration of itself. |
| Session Flow | The current Runtime's canonical live Flow and semantic ordering. | Broadcast delivery mechanics or physical persistence implementation. |
| DJ Moment Engine | Immutable live DJ Moments. | Retention policy, database access or TTS assets. |
| Broadcast | Scoped live distribution, Delivery Sequence, watermark, Replay Log, cursor and subscriptions. | Durable history or persistent replay. |
| Music Backend Observation Boundary | Current playback and Playback Instance Identity. | Persistent Session identity or Session lifecycle. |
| Session persistence service (future) | Durable aggregate and projection writes, schema/version checks and integrity validation. | Domain ownership, provider payloads or rendering. |
| SQLite (future option) | A local storage implementation only. | Session semantics, authorization or product export format. |

## Persistent Session aggregate

Each Session has an immutable `session_id`, one immutable `owner_profile_id`
and, where the Profile participates in one, an immutable Household-scope
reference. It is Profile-owned, not Home Assistant-user owned and not
client-owned. A Profile may have many historical Sessions and at most one
active Runtime under the existing Runtime rule.

The durable aggregate may contain only:

- identity, owner Profile and Household references;
- creation, opening, activation, interruption and ending timestamps;
- lifecycle status and a bounded, machine-readable interruption reason;
- the immutable start selection: Start Strategy, initial Mood, Persona, locale,
  selected room/output reference where safe, and safe Music Backend reference;
- bounded lifecycle and retention metadata, including favorite state;
- durable historical DJMoment projections and their authorization scope; and
- schema and projection versions required for safe reading and migration.

It must not contain OAuth credentials, raw provider payloads, provider account
identifiers that are not safe references, Music DNA, Ask DJ history, Planner
working state, Performance Memory, knowledge execution context, a queue,
temporary media URLs, generated audio or a Playback Instance Identity.

## Lifecycle

The canonical durable lifecycle is deliberately minimal:

```text
OPENING -> ACTIVE -> ENDED
    |          |
    +--------> INTERRUPTED
```

| State | Meaning | Legal transition |
| --- | --- | --- |
| `OPENING` | A Session aggregate was created and its Runtime activation is not yet durably confirmed. | `ACTIVE` or `INTERRUPTED`. |
| `ACTIVE` | One currently authorized Runtime is executing this Session. | `ENDED` or `INTERRUPTED`. |
| `INTERRUPTED` | Live execution stopped without a normal Session end. | Terminal. A later listening experience is a new Session unless a separately approved continuation policy says otherwise. |
| `ENDED` | Normal Session completion has been durably recorded. | Terminal. |

`RESUMED` is not a lifecycle state. If a future re-bootstrap is approved, it
is an immutable lifecycle event on the same eligible Session with a new
Runtime execution identifier. It cannot be inferred from a restored Python
object, a socket reconnect or playback metadata.

## Startup and crash handling

On Home Assistant startup, the future persistence service must reconcile every
locally owned Session left in `OPENING` or `ACTIVE` before any client sees it as
active. It performs one short, idempotent reconciliation transaction.

A future safe re-bootstrap requires all of the following:

1. the owner Profile, Household authorization and selected backend binding are
   still valid;
2. the Session's retention/privacy policy permits re-bootstrap;
3. the selected Observation Boundary currently reports the complete Continue
   Stage 2 capability set;
4. a fresh, authorized Current Playback Projection supplies a valid Playback
   Instance Identity for the still-active occurrence;
5. the Runtime can start with no restored Planner state, Performance Memory,
   Broadcast state, replay data or prior execution object; and
6. a dedicated future policy explicitly authorizes that re-bootstrap path and
   its idempotency and user-visible semantics.

If any prerequisite is absent, the service closes the Session as
`INTERRUPTED`, with reason `home_assistant_restart` or a more precise bounded
reason and a timestamp. It does not retry, guess a playback occurrence, replay
old Moment delivery or recreate a previous Runtime.

The current implementation has no complete Continue Stage 2 observation
implementation. Therefore its only future startup reconciliation outcome is
technical closure as interrupted until a separately authorized capability meets
the complete contract in
[`docs/product/CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md`](docs/product/CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md).

## Historical DJMoment projections

A **Historical DJMoment Projection** is a durable, immutable, renderer-safe
record derived from an already realized DJ Moment. It is not a serialized
Runtime, mutable Session Flow, Broadcast event or provider response.

The projection may contain a stable projection identifier, Session identity,
Moment identity/type, occurred-at timestamp, renderer-safe title/content/
artwork/action data, frozen Presentation Intent, safe playback references and
a per-Moment visibility scope. It must preserve only information that was safe
to present when the Moment was created.

It must never contain generated audio, temporary audio URLs, raw provider
payloads, credentials, Music DNA, Ask DJ history, Performance Memory, Playback
Instance Identity, Broadcast cursor/watermark/sequence, Replay Log entries or
Runtime objects.

Historical projections are Profile-owned by default. Household or shared
visibility is explicit and evaluated per Session and per Moment; it is never
inferred merely because two clients are in one Home Assistant installation.
Access checks run before returning a cached projection, deriving an on-demand
TTS result or opening a historical timeline. Multiple authorized clients may
read the same immutable projection concurrently; each uses independent
transport and temporary rendering resources.

## Durable and ephemeral boundary

| Durable when implemented | Always ephemeral |
| --- | --- |
| Session identity/lifecycle/start metadata/retention/favorite state | Runtime object and execution lock |
| Interrupted/ended timestamps and reasons | Planner working state and Knowledge execution context |
| Historical renderer-safe DJMoment projections | Performance Memory and live Session Flow revision/journal |
| Explicit visibility/authorization projection metadata | Broadcast Delivery Sequence, watermark, Recovery Cursor and Replay Log |
| Safe compact playback references without occurrence identity | Subscriptions, callbacks and client transport state |
| Schema and projection versions | Temporary TTS audio/URLs and Playback Instance Identity |

No durable field may turn Broadcast recovery into persistent replay or turn a
historical projection into a provider playback-control record.

## Consistency and failure semantics

The target ordering for one future durable contribution is:

```text
semantic Session/Flow decision
  -> short idempotent Session/projection transaction
  -> live Broadcast publication
```

Projection writes use an immutable projection identifier and unique durable
key, so retry is idempotent. The persistence service owns transaction
boundaries; Planner, Moment Engine and Broadcast do not open database
transactions.

- If persistence succeeds and Broadcast fails, the durable history remains
  authoritative; a later client receives it through an authorized historical
  read, while live delivery is not fabricated retrospectively.
- Broadcast must not intentionally publish a contribution whose required
  durable projection write failed. A write failure leaves the live capability
  in its defined safe failure path and records no false completion.
- Process termination between commits is reconciled from durable lifecycle and
  projection facts only. It never restores an in-memory Runtime or Replay Log.
- Session ending uses one short transaction for the terminal state and all
  already accepted projection references. A late write is rejected once the
  terminal lifecycle transition commits.

This is local transactional consistency, not distributed event sourcing. No
cross-process queue, persistent Broadcast cursor or exactly-once socket
delivery is introduced by this amendment.

## Storage, migration, backup and export

SQLite is the approved future implementation option for Session persistence,
not the domain owner. A future DJConnect-owned persistence service may keep a
private database under the Home Assistant configuration storage boundary (for
example a DJConnect-managed file below `.storage`). It must use one integration
owned connection policy, WAL-compatible short transactions, integrity checks at
startup, explicit schema metadata and forward-only idempotent migrations.

Home Assistant backup is the installation-level mechanism: it may include the
private database and migration metadata as part of the HA configuration backup.
Restore must validate schema compatibility, integrity and authorization
references before exposing Sessions; invalid or incomplete restored data is
quarantined rather than silently treated as active.

DJConnect product export/import is separate from the physical database. A
future versioned, validated envelope may export eligible Profile and
Session-history projections without credentials, temporary audio, provider raw
payloads or ephemeral execution state. Full installation backup may include
internal storage. Profile export includes only its authorized Profile-owned
data. Session-history export includes only explicitly selected, visible and
retention-eligible historical projections. Playback occurrence data, runtime
recovery infrastructure and secrets belong in neither product export nor
history export.

Retention and cleanup are future persistence-service jobs. They must be
profile/visibility aware, idempotent, auditable without sensitive content, and
run only after authorization and retention policy are available.

## Voice and renderer boundary

This amendment records two future, separate rendering paths:

1. **Autonomous live room voice** consumes the current live DJMoment. Home
   Assistant resolves the active output's room and selects an eligible
   DJConnect Voice Satellite in that room. It does not require a client-side
   output-device selector.
2. **User-initiated replay** accepts one current or authorized historical
   DJMoment, generates TTS on demand server-side and lets the requesting
   client play its independent temporary result.

Authorization precedes any cache lookup or TTS result for both paths.
Generated audio is never canonical Session state. The Wall Pi remains a native
QML Renderer Host; Universal Session Receiver is a projection protocol and does
not authorize a Chromium-kiosk replacement.

## Bounded implementation roadmap

Each item is a separate capability with its own Pre-Flight, implementation,
validation, merge and finalization.

1. **Persistence foundation:** DJConnect storage service, schema metadata,
   migration runner, integrity checks and test harness; no Session writes yet.
2. **Persistent Session lifecycle store:** aggregate identity/states and
   idempotent lifecycle transitions; no historical projections or re-bootstrap.
3. **Startup reconciliation:** deterministic interrupted closure for open
   Sessions; re-bootstrap remains unavailable until its strict prerequisites
   exist.
4. **Historical Session and DJMoment projections:** immutable renderer-safe
   projections and owner/visibility authorization reads.
5. **Retention and cleanup:** bounded policy, favorite protection and
   auditable cleanup.
6. **Backup/restore integration:** integrity and compatibility validation for
   installation backup/restore.
7. **Versioned Profile and Session-history export/import:** product envelopes
   independent of SQLite.
8. **On-demand DJMoment voice replay:** authorized current/historical TTS
   generation with temporary delivery only.
9. **Autonomous room-aware HA voice:** eligible Satellite selection for the
   active room's live Moment.
10. **Renderer adoption:** native Apple replay presentation and native Pi QML
    support, without changing Renderer ownership.

Continue Stage 2 re-bootstrap is not scheduled by this architecture. It may
be considered only after its independently gated Observation Boundary and
Playback Instance Identity contract are implemented and verified.

## Explicit non-goals

This amendment does not implement SQLite, schemas, repositories, migrations,
Session writes, restart recovery, Runtime serialization, historical storage,
TTS endpoints/caching, backup/restore, product import/export, replay controls,
voice delivery, renderer changes, Continue Stage 2 or providers.

## Related records

- [`DJCONNECT_V4_ARCHITECTURE.md`](DJCONNECT_V4_ARCHITECTURE.md)
- [`DJ_SESSION_RUNTIME_CONTRACTS.md`](DJ_SESSION_RUNTIME_CONTRACTS.md)
- [`docs/product/DJ_SESSION_DOMAIN_MODEL.md`](docs/product/DJ_SESSION_DOMAIN_MODEL.md)
- [`SESSION_FLOW_RECOVERY_ARCHITECTURE.md`](SESSION_FLOW_RECOVERY_ARCHITECTURE.md)
- [`docs/product/CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md`](docs/product/CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md)
