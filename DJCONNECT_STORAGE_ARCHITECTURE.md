# DJConnect Storage Architecture

**Status:** Canonical architecture and implemented-foundation record
**Owner:** Home Assistant integration
**Scope:** Ownership, lifecycle and recovery of all DJConnect storage.

## Why this record exists

`PERSISTENT_SESSION_ARCHITECTURE.md` owns durable DJ Session semantics and
`docs/technical/CLIENT_STORAGE.md` owns the observed client-storage inventory.
Neither defines the cross-host ownership, backup, import and recovery contract.
This document is therefore the single canonical storage architecture. It links
to those narrower records instead of restating their domain or inventory detail.

## Decision

The Home Assistant integration is the sole authoritative owner of persistent
DJConnect data. A renderer may retain only device-local state needed to present
or recover its experience. It is never authoritative for Profiles, Music DNA,
Ask DJ history, recommendations, Session history, device/profile associations,
DJPrints or canonical runtime facts.

```text
Profile → Session Runtime → Planner → Knowledge → DJ Moment → Session Flow
        server-owned runtime and canonical persistence
                                      ↓
                         safe projections / temporary derivatives
                                      ↓
                               Renderer hosts
```

Renderer recovery is always pairing (or browser authorization), server sync,
and rebuilding disposable local storage. There are no renderer backup formats.

## Repository evidence inventory

| Concern | Current implementation | Classification | Authoritative owner |
| --- | --- | --- | --- |
| Profile, preferences, device/profile mappings, backend references | HA `Store` key `djconnect_profile_platform` | Canonical | HA integration |
| Music DNA | HA `Store` key `djconnect_music_dna` | Canonical, opt-in | HA integration |
| Ask DJ history | HA `Store` key `djconnect_ask_dj_history` | Canonical, user-scoped | HA integration |
| Pairing, OAuth and integration options | HA config entries/options | Canonical configuration; secret-bearing | HA integration |
| Session Runtime, Planner, Performance Memory, live Session Flow | Python runtime objects | Runtime only | HA process; never persisted as runtime |
| Persistent Session metadata and historical Moment projections | integration-owned SQLite schema/migrations | Canonical foundation | HA integration |
| DJPrint Library and publication state | no implementation | Missing/deferred | Future HA server store |
| Browser receiver state | renderer projection/session state only | Projection/cache | Browser, non-authoritative |
| Publication assets | no implementation | Derived/cache | Publication host, non-authoritative |

The integration-owned persistence platform is the only SQLite connection and
migration owner. It stores `.storage/djconnect.sqlite3`, validates integrity,
uses forward-only migrations and exposes only repository transaction boundaries.
Existing HA Store records remain canonical until a separately approved,
lossless server migration moves a specific aggregate; no parallel authority is
created by this architecture.

## Storage profiles

| Profile | May retain | Must not own | Recovery |
| --- | --- | --- | --- |
| **Server Storage** | Canonical profiles, preferences, associations, Music DNA, Ask DJ history, durable history, DJPrint semantic objects/provenance, schema and export metadata | Live Runtime objects merely because a store exists | HA restore, import or normal server startup |
| **Rich Native Client** (Apple/Windows) | secure device state, local preferences, projections, pending intents, assets, replay cache, cursors | profiles, history, Music DNA, recommendations, DJPrint Library, backups | pair and synchronize; local data is rebuildable |
| **Browser Receiver** (Universal Receiver/VibeCast) | browser authorization, current projections, renderer preferences, temporary assets, IndexedDB/Cache Storage/sessionStorage | durable pairing, profile/history ownership, backups | authorize and fetch a current projection |
| **Persistent Publication Host** (future Pico) | provisioning, device identity/configuration, firmware/OTA state, manifest, current/previous rendered asset and checksum | DJPrint semantic object, profile or library ownership | provision and regenerate/download derivative |
| **Embedded Interaction Host** (ESP32) | secure device state, provisioning, bounded interaction/pending-intent/projection/asset/replay state, firmware | profile database, Music DNA, Ask DJ history, Session Flow history, backups | pair and synchronize; bounded state may be discarded |

## Storage class matrix

`Y`, `N` and `C` mean yes, no and conditional on the stated policy. `L/U/S/R/B`
mean survives logout, unpair, session end, local reinstall and HA restore.
`Server` is the canonical owner for every class; renderer entries are permitted
copies only. The machine-readable implementation registry is
`custom_components/djconnect/persistence/ownership.py`.

| Class | Eligible hosts | Durability / confidentiality | L/U/S/R/B | Rebuild source and deletion/versioning |
| --- | --- | --- | --- | --- |
| Secure Device State | server, native, embedded | durable; secret/device-confidential | C/N/Y/N/Y | server pairing record; unpair rotates/deletes local credential; versioned pairing protocol |
| Preferences | server, all renderers | server durable; local copy non-secret | C/Y/Y/N/Y | profile/default preferences; reset local on logout; profile schema version |
| Projection Store | server, all renderers | bounded/cache; privacy-scoped | N/N/C/N/Y | current server projection; invalidate on revision, privacy/profile change or unpair |
| Pending Intent Store | server, native, embedded | short-lived; confidential | N/N/N/N/N | server intent/confirmation contract; expiry or execution deletes it |
| Asset Cache | server, all renderers | bounded derived asset | N/N/C/N/N | safe server/media reference; TTL, checksum or privacy change invalidates it |
| Voice Replay Cache | server, native, embedded | bounded temporary audio; confidential | N/N/N/N/N | server-generated temporary replay; TTL/session end/unpair deletes it |
| Publication Asset Store | server, publication host | durable derivative; non-canonical | C/C/Y/C/Y | canonical DJPrint + composition/manifest; checksum mismatch or new render replaces it |
| Embedded Interaction State | server, embedded | bounded device-local interaction state | N/N/N/N/N | current server projection; session end, unpair or firmware reset deletes it |
| Canonical Profile Store | server only | durable; profile-confidential | Y/C/Y/Y/Y | HA Store/import; explicit profile deletion/reassignment; schema-versioned |
| Canonical History Store | server only | durable; profile/visibility-confidential | Y/C/Y/Y/Y | HA Store/SQLite/import where eligible; retention or profile deletion removes it |
| Canonical DJPrint Store | server only | durable immutable semantic/provenance record | Y/C/Y/Y/Y | future HA store/import; retention/deletion policy; immutable schema/version |
| Schema and Migration State | server only | durable internal metadata | Y/Y/Y/Y/Y | migration registry and HA backup; forward-only, no downgrade |

Runtime objects — Session Runtime, Planner working state, Performance Memory,
live Session Flow, Broadcast cursors and temporary provider/audio data — are
not storage classes. They end with their runtime. A DJMoment becomes durable
only through explicit immutable historical projection/materialization. A
DJPrint is created only by explicit materialization and remains a Profile-owned
semantic object; rendered images are derivatives, never its canonical form.

## Import, export, backup and restore

All lifecycle operations are server-owned. Clients may request an authorized
operation but never create their own canonical backup or restore format.

### Product export and import

Profile export is versioned and validated. It may contain portable profile
metadata, preferences, allowed Music DNA/recommendation/like-dislike references,
durable profile history and eligible DJPrint semantic records when those
capabilities exist. It contains schema/export and integrity metadata.

It never contains OAuth/access/refresh/device/APNs tokens, passwords, proofs,
raw credentials, machine-specific secrets, raw audio, temporary URLs or a
serialized Runtime. Imported providers are re-authorized and renderer devices
are re-paired. Installation export is a separate future envelope containing
non-secret installation settings plus multiple profile envelopes; it is not a
replacement for a Home Assistant backup.

Imports validate format and schema before changing state, reject secret-bearing
payloads, are explicit `merge` or `replace`, detect identity collisions, and
use one server transaction where the target store supports it. Failed validation
or transaction work leaves prior server state intact. Forward-only migrations
have no downgrade path; a newer or malformed store fails closed.

### Home Assistant backup and restore

HA's normal configuration backup is the installation backup mechanism. It
contains Home Assistant Store/config-entry state and the integration-owned
`.storage/djconnect.sqlite3` when the HA configuration directory is backed up.
On restore, the integration validates Store/schema data, SQLite integrity and
migration history before use. Renderer caches are discarded and rebuilt;
renderers re-pair or re-authorize when their local secure state, provider
credentials or central relay registration is absent or invalid. A product
export excludes secrets even where an encrypted HA backup may contain
HA-managed configuration credentials.

## Migration and deletion policy

The integration owns one ordered migration registry with immutable version,
identifier and checksum. Startup checks integrity, rejects a future or
inconsistent schema, applies one forward migration per transaction, then
validates shape and migration history. Migration tests cover upgrade, failure
rollback and rejection safety.

Logout removes local identity-bound copies; unpair removes or rotates device
credentials and invalidates projections; session end removes runtime,
pending-intent and temporary replay state; profile deletion removes its
canonical personal state subject to explicit reassignment/retention rules. No
cache survives as authority.

## Implemented foundation and deferred work

Implemented: HA Store-backed canonical aggregates; profile export/import
validation and secret exclusion; integration-owned SQLite lifecycle, integrity,
transaction and migration platform; ownership registry and regression tests.

Deferred: a lossless consolidation migration of existing HA Store aggregates,
DJPrint Library/domain and export, installation export, publication hosts,
client databases, renderer implementations, retention jobs and product-facing
backup/restore UI. Those need separate bounded capabilities and may not move
ownership out of Home Assistant.

## Related canonical records

- `PERSISTENT_SESSION_ARCHITECTURE.md` — durable Session and Moment semantics.
- `docs/technical/CLIENT_STORAGE.md` — observed client/repository inventory.
- `DJCONNECT_V4_ARCHITECTURE.md` — server Runtime and renderer ownership.
- `custom_components/djconnect/persistence/README.md` — provider implementation.
