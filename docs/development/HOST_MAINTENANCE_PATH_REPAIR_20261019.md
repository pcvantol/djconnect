# Relocated verification-maintenance path repair

## Scope and admission

The owner explicitly authorized this bounded migration repair on 19 October
2026, including an exception to the host-readiness gate for this repair alone.
The baseline is `053ce3cb0673e8271df9191f80fa08654ea1945d`. The existing Core
writer preserves the separate avatar WIP and archived-session-erasure branch.
This is host-bootstrap maintenance, not a new product capability or deployment.

## Problem and correction

The existing verification-artifact cron still referenced a pre-migration GitHub
root. The verifier generated an unquoted command, so simply substituting a root
containing spaces would produce an invalid shell command. Bootstrap 2.0.22 now
constructs the expected line using shell-escaped script and log paths and also
escapes cron's percent syntax. Space-free roots retain their prior command.
The component version and aggregate manifest hashes are updated together.

The separately authorized local transaction backed up and replaced only the
existing marked verification-artifact block, checked for a concurrent edit and
read the exact new crontab back. Its existing `0 3 * * *` schedule and all other
cron blocks remain unchanged. No cleanup was executed by this transaction.

## Qualification and limitations

Four focused regressions cover the unchanged legacy schedule, actual execution
of a fixture under a path with spaces and shell metacharacters, cron percent escaping, and installer/verifier parity. Only the fixture script executes; no real cleanup is part of tests.
Shell syntax, manifest integrity, targeted Ruff and diff validation pass.
Independent bounded source review found no blocker in the inspected change.
The complete onboarding-script/package suite ran 72 tests: OK, with seven
conditional skips. Offline development-projection validation also passes.

An earlier verifier-only candidate reported exit 0 with onboarding 4.5.3 after
the bounded cron replacement. CI then correctly rejected its stale packaged
test bundle. The final correction publishes a new deterministic onboarding
4.5.4 bundle and retains every earlier distribution unchanged. Canonical pins
advance together; the qualification policy and checks are not relaxed.
Canonical-main readiness must be read back after protected source delivery;
the earlier candidate receipt is not a final 4.5.4 readiness claim.

The 4.5.4 installer writes the same escaped cron line as the verifier. An owning
installer regression runs the exact function with inert crontab/launchd/delete
services and verifies preservation of an unrelated cron entry. The original
4.5.3 distribution is unchanged. No full onboarding/recovery run is inferred
from this narrow qualification. This increment does not restart paused automations,
change Home Assistant, publish an avatar contract or close any product feature.

## Delivery

Decision: source correction locally qualified; protected PR and separate
Finalization pending. No protection, review or exact-candidate authorization
check is bypassed by the host-readiness exception. The same preserved avatar
assignment resumes only after canonical host readiness is established.
