# Execution Host Configuration Resolver

Date: 2026-08-03

## Objective

Establish one provider-neutral Execution Host Configuration Resolver over the
canonical Engineering Platform configuration. It owns transport, Inbox, local
stores, runtime resolution, telemetry storage and safe host identity. Forge,
the Execution Host Contract and future transports remain out of scope.

## Delivered outcome

PR [#722](https://github.com/pcvantol/djconnect/pull/722), **Add Execution
Host Configuration Resolver**, merged as
`6412e0879da779d78e46e968ccda12b0ca3d47ee`.

The resolver exposes provider-neutral Runtime Prompt transport, status, report,
log and telemetry stores, runtime executable and safe host identity. The
current iCloud transport is now resolver-owned. Preflight and Inbox consumers
request resolved capabilities instead of embedding transport details, while the
dashboard presents only host name, version, runtime and transport.

## Validation evidence

- `python3 -m unittest discover -s tests/engineering`: 240 passed.
- `node --check tools/engineering/assets/dashboard.js`: passed.
- `git diff --check`: passed.

## Follow-up

The recommended next increment is Execution Host Preflight Level 3 (Capability
Preflight). It remains separate from transport resolution and Forge.
