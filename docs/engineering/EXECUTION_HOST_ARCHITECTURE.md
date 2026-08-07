# Execution Host architecture

The Execution Host owns the Engineering lifecycle, checkpoints and terminal
evidence. It does not own platform process execution or dashboard projection.

- `execution_host.py` coordinates a single bounded lifecycle.
- `execution_lease.py` owns SQLite-backed active-run ownership and liveness.
- `execution_readiness.py` selects and evaluates one typed readiness profile.
- `providers.py` is the process/platform boundary. Codex, local Git, launchd,
  iCloud transport and Tailscale interactions are implemented there; lifecycle
  code consumes provider methods.

Readiness has three explicit profiles: platform host, Managed repository and
Genesis target. A Genesis run only evaluates its target profile; a Managed run
only evaluates its repository profile. JSON status files are projections, not
an ownership or lifecycle authority.

Each admitted run persists a typed readiness decision in the canonical
datastore. The policy defines requirements; preflight and providers acquire
facts; the Execution Host only responds to the resulting decision.

The current migration inventory intentionally retains process calls in
dashboard diagnostics, qualification helpers and logging utilities. They are
read-only/supporting components and are outside the Execution Host lifecycle
boundary; future provider migration must preserve that separation rather than
moving lifecycle decisions into providers.
