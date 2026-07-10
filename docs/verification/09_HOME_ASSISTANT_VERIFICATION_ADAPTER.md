# Verification Program V1
## Phase 9 - Home Assistant Verification Adapter

Status: Implemented

The Home Assistant Verification Adapter is the first production-quality
platform adapter. It exposes Home Assistant runtime primitives to the
Verification Core while staying intentionally thin.

The adapter answers only:

> How do I perform this operation on Home Assistant?

It never decides whether a scenario succeeded. Scenario interpretation remains
owned by the Scenario Engine and Verification Core.

## Architecture

```text
Scenario
  -> Verification Planning Engine
  -> Verification Core
  -> Verification Execution Environment
  -> Home Assistant Verification Adapter
  -> Home Assistant Runtime
  -> Evidence and raw runtime results
  -> Verification Core
```

The adapter extends existing Verification subsystems only. No new architecture
layer is introduced.

## Responsibility Boundary

The adapter owns runtime execution primitives:

- connection lifecycle;
- health checks;
- capability discovery;
- REST requests;
- websocket requests where a websocket transport is available;
- generic service calls;
- Home Assistant restart/reload service primitives;
- state and registry inspection;
- approved DJConnect storage snapshots;
- namespaced fixture creation and removal;
- runtime logs;
- runtime and environment metadata;
- artifact metadata hooks.

The adapter does not own:

- scenario selection;
- verification planning;
- assertions;
- Profile logic;
- Privacy logic;
- Music DNA logic;
- pass/fail criteria;
- build qualification;
- repository hygiene;
- GitHub CI inspection;
- secrets management;
- cleanup of non-adapter resources.

## Configuration

Configuration is externalized through environment variables:

- `DJCONNECT_VERIFICATION_HA_URL`;
- `DJCONNECT_VERIFICATION_HA_TOKEN`;
- `DJCONNECT_VERIFICATION_HA_STORAGE_DIR`;
- `DJCONNECT_VERIFICATION_HA_LOG_PATH`;
- `DJCONNECT_VERIFICATION_HA_TIMEOUT`;
- `DJCONNECT_VERIFICATION_FIXTURE_NAMESPACE`;
- `DJCONNECT_VERIFICATION_ALLOW_DESTRUCTIVE`.

The CLI opt-in is:

```bash
python3 -m tools.verification.cli --ha-adapter execute --scenario-id PROFILE-001
```

Without `--ha-adapter`, execution remains skipped because no platform adapter is
registered.

## Runtime API

Implemented primitives:

- `initialize()`;
- `shutdown()`;
- `health()`;
- `version()`;
- `capabilities()`;
- `restart_runtime()`;
- `reload_djconnect()`;
- `execute_rest()`;
- `execute_websocket()`;
- `execute_service()`;
- `call_service()`;
- `wait_for_event()`;
- `get_state()`;
- `list_entities()`;
- `get_device()`;
- `list_devices()`;
- `get_area()`;
- `list_areas()`;
- `snapshot_storage()`;
- `compare_storage()`;
- `create_fixture()`;
- `remove_fixture()`;
- `collect_logs()`;
- `collect_environment()`;
- `collect_artifact_metadata()`;
- `cleanup()`;
- `reset()`.

REST results preserve:

- status;
- headers;
- timing;
- body;
- method;
- path.

Responses are not normalized into DJConnect behavior. They are only redacted and
returned as structured runtime data.

## REST

The adapter uses documented Home Assistant HTTP APIs and documented DJConnect
runtime routes. It does not invent routes.

The current implementation supports generic REST through:

```python
execute_rest(method, path, payload=None, headers=None)
```

## WebSocket

The adapter exposes `execute_websocket(message)`. A mock websocket transport is
used by tests. The default stdlib transport reports `CapabilityUnavailable`
unless a websocket-capable transport is injected.

This keeps the adapter thin and avoids adding a new dependency solely for Phase
9. Future live websocket support can extend the existing transport hook.

## Services

The adapter supports generic service execution:

```python
execute_service("domain.service", payload)
call_service("domain", "service", payload)
```

Restart and reload are exposed as runtime primitives, not scenario behavior.

## Fixture Model

The adapter supports namespaced in-memory verification fixtures:

- `verification-profile-*`;
- `verification-device-*`;
- `verification-area-*`;
- `verification-backend-*`;
- `verification-household-*`.

It refuses to remove fixture IDs outside these prefixes.

The first implementation deliberately avoids direct mutation of real Home
Assistant storage. This protects production objects while still enabling the
Scenario Engine to prove fixture lifecycle behavior.

## Storage

Approved storage keys:

- `djconnect_profile_platform`;
- `djconnect_music_dna`;
- `djconnect_ask_dj_history`.

The adapter can snapshot these files when
`DJCONNECT_VERIFICATION_HA_STORAGE_DIR` is configured. It refuses arbitrary Home
Assistant storage keys.

Direct storage mutation is not implemented.

## Logging and Evidence

The adapter records sanitized runtime operation logs:

- timestamp;
- operation;
- transport;
- duration;
- result;
- redacted data.

The redaction policy covers keys containing:

- `token`;
- `password`;
- `secret`;
- `proof`;
- `authorization`;
- `prompt`;
- `history`;
- `memory`;
- `raw_audio`.

The adapter uses the existing Verification evidence/log redaction helpers and
does not introduce another logging framework.

## Environment Integration

The adapter does not duplicate Execution Environment responsibilities.

Repository hygiene, toolchain validation, dependency validation, environment
snapshots, artifact management, GitHub CI and cleanup remain owned by the
Verification Execution Environment and Verification Core.

## First Scenario Set

The Scenario Engine now expands the canonical catalog scenarios:

- `PROFILE-001`;
- `PROFILE-002`;
- `PROFILE-003`;
- `PROFILE-004`;
- `PROFILE-005`.

For these scenarios it executes runtime primitives through the Home Assistant
adapter:

- collect runtime environment;
- health check;
- capability discovery;
- create isolated fixture;
- snapshot approved Profile Platform storage;
- collect logs;
- remove isolated fixture.

The adapter performs these operations only. It does not inspect Profile
semantics or evaluate scenario assertions.

## Limitations

- Default websocket transport reports `CapabilityUnavailable` unless a
  websocket-capable transport is injected.
- Live HA execution requires explicit `--ha-adapter` plus HA URL/token
  configuration.
- Runtime fixture creation is currently isolated in adapter memory and does not
  mutate real Home Assistant objects.
- Approved storage snapshots require an explicit storage directory.
- Live tests are opt-in and skipped or blocked states must not be reported as
  PASS.

## Future Extensions

Recommended next runtime primitives:

- injected live websocket transport;
- Home Assistant config entry reload by entry id;
- read-only device and area registry websocket commands where HA REST routes are
  unavailable;
- evidence file emission for live adapter logs;
- opt-in fixture creation through documented DJConnect verification services if
  such services are later approved.

These are extensions of the existing adapter and Verification subsystems, not
new architecture layers.
