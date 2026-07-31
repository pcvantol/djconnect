# Canonical DJConnect storage architecture

**Status:** Implemented through PR #646
**Implementation merge:** `f33f63ff399599b46c220c5169875abbda230f9a`

## Immutable implementation prompt

You are working in the canonical DJConnect Home Assistant integration repository.
Task
Define, consolidate and implement the canonical DJConnect storage architecture.
This is a repository-first architecture increment.
Do not redesign the DJConnect runtime.
Do not introduce a second source of truth.
Do not move canonical ownership into renderer hosts.
Do not create parallel architecture documentation when the repository already contains canonical documentation covering storage, persistence or lifecycle.
Repository-first rule
Before making any architectural decision:
1. Inventory existing architecture, ADR, persistence, profile, runtime, storage, lifecycle and migration documentation.
2. Determine where storage ownership is already documented.
3. Extend existing canonical documentation wherever possible.
4. Only introduce a new document if no appropriate canonical location exists.
5. If a new document is required:
	- explain why;
	- link it from the existing canonical architecture;
	- avoid duplicating existing content.
The repository must continue to have one canonical source of truth for storage architecture.
Context
DJConnect V4 runtime:
Profile
→ Session Runtime
→ Session Planner
→ Knowledge Engine
→ DJ Moment Engine
→ immutable DJMoment
→ Session Flow
→ Broadcast
→ Renderer Hosts
The Home Assistant integration owns canonical runtime and business logic.
Renderer hosts include:
- Apple
- Windows
- native Raspberry Pi renderers
- ESP32 appliances
- Universal Receiver
- VibeCast
- future Pico publication hosts
- future Gallery Hosts
Core ownership rule
The Home Assistant integration is the single authoritative owner of persistent DJConnect data.
Renderer hosts may store only the information necessary to provide their local experience.
Renderer hosts must never become authoritative owners of:
- profiles
- Music DNA
- Ask DJ history
- DJPrint Library
- recommendations
- session history
- device registry
- profile configuration
- canonical runtime data
Import, export, backup, restore and migration are server-owned capabilities.
Do not introduce:
- Apple backup
- Windows backup
- Pi backup
- Browser backup
- ESP32 backup
- Pico backup
A renderer must always be recoverable by:
1. pairing (or browser authorization)
2. synchronization from the canonical server
3. rebuilding disposable local storage
Objectives
1. Inventory the current persistence implementation.
2. Inventory existing storage documentation.
3. Identify authoritative ownership.
4. Consolidate storage documentation.
5. Define canonical storage profiles.
6. Define storage classes.
7. Define backup/import/export contracts.
8. Define migration responsibilities.
9. Implement only the smallest justified foundation.
10. Document deferred work.
Repository assessment
Before changing code:
Inventory current persistence mechanisms.
Identify:
- Home Assistant Storage usage
- config entries
- registries
- storage helpers
- JSON stores
- database usage
- migration framework
- existing persistence interfaces
Locate ownership for:
- profiles
- devices
- Music DNA
- recommendations
- Ask DJ history
- Session Runtime
- Session Flow
- DJMoment
- DJPrint
- browser receiver state
- publication state
Classify each as:
- canonical
- projection
- runtime
- cache
- duplicated
- missing
- obsolete
Determine how current persistence participates in:
- HA backup
- HA restore
- schema migration
Determine which architecture documentation already owns these concepts.
Canonical storage profiles
Define these storage profiles.
1. Server Storage
Canonical Home Assistant persistence.
Owns authoritative persistent information including where applicable:
- profiles
- profile preferences
- Music DNA
- response preferences
- mood preferences
- DJ persona
- linked music services
- linked playback devices
- paired renderer devices
- profile associations
- Ask DJ history
- recommendations
- likes
- dislikes
- durable profile history
- DJPrint Library
- DJPrint provenance
- schema metadata
- migration metadata
- export metadata
- installation metadata
Session Runtime and Performance Memory remain runtime-scoped unless explicitly materialized.
Do not persist runtime objects simply because storage exists.
2. Rich Native Client Storage
Apple and Windows.
Permitted:
- Secure Device State
- Preferences
- Projection Store
- Pending Intent Store
- Asset Cache
- Voice Replay Cache
- offline navigation metadata
- sync cursors
This storage is rebuildable.
It is never authoritative.
3. Browser Receiver Storage
Universal Receiver
VibeCast
Permitted:
- session authorization
- current projections
- renderer preferences
- temporary assets
- IndexedDB when useful
- Cache Storage
- sessionStorage
Forbidden:
- durable pairing
- profile ownership
- history ownership
- backups
Browser storage is disposable.
4. Persistent Publication Host Storage
Future Pico publication hosts.
Permitted:
- provisioning
- device identity
- renderer configuration
- firmware state
- OTA state
- publication manifest
- rendered publication asset
- previous rendered asset
- checksum
Forbidden:
- DJPrint ownership
- profile ownership
- library ownership
Canonical flow:
Profile-owned DJPrint
→ Composition
→ rendered publication asset
→ publication cache
5. Embedded Interaction Host Storage
ESP32 appliances.
Permitted:
- Secure Device State
- pairing
- provisioning
- Embedded Interaction State
- Projection Store
- Pending Intent Store
- bounded Asset Cache
- bounded Voice Replay Cache
- firmware state
Forbidden:
- profile database
- Music DNA ownership
- Ask DJ history
- DJPrint Library
- Session Flow history
- backups
Storage classes
Define consistent ownership for:
- Secure Device State
- Preferences
- Projection Store
- Pending Intent Store
- Asset Cache
- Voice Replay Cache
- Publication Asset Store
- Embedded Interaction State
- Canonical Profile Store
- Canonical History Store
- Canonical DJPrint Store
- Schema and Migration State
For every class define:
- authoritative owner
- eligible hosts
- durability
- confidentiality
- lifetime
- survives logout
- survives unpair
- survives session end
- survives reinstall
- survives HA restore
- rebuildable
- rebuild source
- deletion behaviour
- versioning
Import / Export / Backup
Server owns all lifecycle operations.
Profile Export
Should include portable canonical data where appropriate.
Assess inclusion of:
- profile metadata
- preferences
- Music DNA
- Ask DJ history
- recommendations
- likes/dislikes
- DJPrint Library
- durable profile history
- compatible device associations
- schema version
- export version
- integrity metadata
Never export:
- secrets
- access tokens
- machine-specific credentials
Where required:
re-authorize providers
re-pair devices
Full Installation Export
Assess whether installation export should wrap:
- installation settings
- multiple profile exports
Keep separate from HA platform backup.
Home Assistant Backup
Verify how canonical persistence participates in HA backup.
Document:
- automatically protected data
- external dependencies
- restore behaviour
- migration behaviour
- required re-pairing
- required re-authorization
Import
Imports must be:
- versioned
- validated
- atomic where practical
- explicit merge/replace
- collision safe
- rollback safe
Restore
Restore preserves canonical identity where appropriate.
Renderer hosts reconnect.
Renderer caches rebuild.
Migration
Migration belongs exclusively to canonical storage.
Document:
- schema versioning
- migration registry
- ordering
- rollback strategy
- downgrade behaviour
- migration tests
DJPrint
DJPrint is:
- immutable
- profile-owned
- durable
Server owns:
- semantic object
- provenance
- source references
- editorial content
- privacy metadata
- retention metadata
- schema version
Publication hosts own only:
- rendered derivatives
- manifests
Never store only rendered images as canonical DJPrint.
Runtime lifecycle
Maintain explicit distinction between:
Session Runtime
Performance Memory
DJMoment
DJPrint
Projection
Caches
Performance Memory remains runtime-only.
DJPrint is created only by explicit materialization.
Documentation
Prefer updating existing canonical architecture documentation.
Only create new documentation if justified after repository assessment.
Avoid duplicated architecture.
Implementation boundary
Implement only repository-supported foundations.
Examples:
- storage ownership types
- schema metadata
- migration registry
- storage interfaces
- export envelopes
- validation
- tests
- documentation
Do not implement:
- client databases
- composition engine
- publication hosts
- Samsung Frame integration
- Pico firmware
- renderer implementations
Required decisions
Produce explicit decisions for:
1. Canonical persistence mechanism
2. Ownership unit
3. Profile export contents
4. Installation-only data
5. Never-exported data
6. Secret handling
7. Import semantics
8. Schema versioning
9. Migration registration
10. Client recovery
11. Publication host recovery
12. Browser recovery
13. Projection invalidation
14. Session-end deletion
15. Unpair deletion
16. Restart persistence
17. HA restore behaviour
18. Disposable state
Testing
Add or update tests covering:
- canonical persistence
- runtime state not persisted
- projections rebuild
- cache deletion
- export versioning
- invalid import rejection
- rollback safety
- secret exclusion
- identity collision handling
- migration upgrades
- migration failure safety
- DJPrint export/import
- publication assets not canonical
- browser session expiry
- unpair behaviour
- renderer resynchronization
Deliverables
1. Repository evidence inventory.
2. Updated canonical architecture documentation.
3. Storage profile matrix.
4. Storage class matrix.
5. Import/export/backup contract.
6. Migration strategy.
7. Minimal implementation foundation.
8. Tests.
9. Updated roadmap/status references.
10. Deferred work list.
11. Finalization summary.
Finalization summary
Return:
- assessment outcome
- repository evidence
- documentation updated
- files changed
- canonical decisions
- implemented foundation
- validation results
- migration impact
- backup impact
- security impact
- deferred work
- remaining risks
- recommended next increment
Acceptance criteria
Complete only when:
- the existing canonical architecture has been updated (or a new document has been explicitly justified);
- the Home Assistant integration is documented as the canonical storage owner;
- all five storage profiles are defined;
- storage classes are documented;
- import/export/backup are server-owned;
- runtime, canonical, projection and cache data are clearly separated;
- DJPrint remains profile-owned and semantic;
- browser storage remains session-scoped;
- renderer hosts remain rebuildable from the server;
- no renderer backup formats are introduced;
- migrations are explicit and versioned;
- implementation remains justified by repository evidence;
- tests support the implemented behaviour;
- architecture documentation remains internally consistent.
