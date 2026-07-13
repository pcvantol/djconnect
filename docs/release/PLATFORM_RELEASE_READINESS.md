# Platform Release 3.3 — Readiness

## Canonical result

```text
BLOCKED
```

The release orchestrator evaluated the complete dry-run input bundle and
returned the following blocking condition:

| Subject | State | Reason |
| --- | --- | --- |
| Coverage | `BLOCKED` | `coverage` evidence state is `PENDING`. |

The independent website candidate test also fails: `65/66` tests pass, but
the release renderer detects `3.2.16` asset references across generated,
localized source pages while the candidate version is `3.3.0`.

Certification remains `NOT_CERTIFIED`. The readiness outcome is objective;
there is no manual approval override.
