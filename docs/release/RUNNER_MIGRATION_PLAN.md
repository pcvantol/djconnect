# Self-Hosted Runner Migration Plan

Status: `MIGRATION_IN_PROGRESS`

## Ordered migration

1. Register repository-scoped runners with the canonical labels and prove
   online/trusted/toolchain/workspace/evidence controls. **In progress:** all
   required runners are online; Apple and firmware isolated probes passed.
2. Migrate Apple, Windows, firmware, Pi, Home Assistant, API and website
   platform jobs to explicit qualified runner selectors.
3. Add one runner-evidence artifact to each migrated build/deployment workflow.
4. Dispatch representative non-publishing qualification workflows and verify
   that their recorded runner labels match the required role.
5. Enable the `INTERNAL_RELEASE` gate only after every required runner and
   workflow result is valid.

## Workflow migration rules

- Apple workflows: `[self-hosted, internal-release, qualification, apple]`.
- Windows workflows: `[self-hosted, internal-release, qualification, windows]`.
- ESP32 workflows: `[self-hosted, internal-release, qualification, firmware]`.
- Pi workflows: `[self-hosted, internal-release, qualification, raspberry-pi]`.
- Home Assistant package workflows: `[self-hosted, internal-release, qualification, home-assistant]`.
- API and website deployment workflows: `[self-hosted, internal-release, qualification, production]`.

Existing public-release, App Store, TestFlight, Microsoft Store and public
customer rollout paths are not dispatched by this migration. They require a
separate release profile and channel authorization.

Because the repositories are public, a self-hosted platform job must be gated
to trusted internal events. Fork pull requests must never reach a runner with
build, signing, deployment or local-network capability. This guard is part of
the workflow migration and runner qualification evidence.

## Safety rule

No workflow selector is changed before its target runner is online and has a
passing qualification record. A missing/offline/label-mismatched runner blocks
the release; it never falls back to a GitHub-hosted or Codex execution path.
