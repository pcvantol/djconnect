# Internal Release Runner Policy

Status: `ACTIVE_FOR_MIGRATION`; `INTERNAL_RELEASE_BLOCKED`

## Policy

An internal platform release may be orchestrated by Codex, but every platform
build, package, signing action, artifact publication hand-off and deployment
must execute in GitHub Actions on the assigned qualified self-hosted runner.
Codex must not invoke platform compilers, Xcode, `dotnet publish`, PlatformIO,
package builders, signing commands or direct artifact publication.

Public-repository fork pull requests are not trusted internal events. They must
not execute a self-hosted platform job. A missing or ineffective fork guard is
a release-blocking runner-policy failure.

## Mandatory gate

`INTERNAL_RELEASE` is `PASS` only when all of the following are evidenced for
the same candidate SHA:

- all required role runners are online and qualified;
- each platform workflow completed on its required self-hosted labels;
- artifacts, hashes, test evidence and coverage evidence are present;
- Verification Runtime, Software Assurance and Trusted Delivery are `PASS`;
- version alignment and candidate-SHA qualification are `PASS`; and
- deployment and rollback evidence are present where the profile performs
  deployment.

Any missing, stale, failed or label-mismatched item returns
`INTERNAL_RELEASE_BLOCKED` with the associated runner/workflow/evidence cause.

## Current decision

`INTERNAL_RELEASE_BLOCKED`: all required runners are registered and online,
and Apple/firmware isolated runner probes passed, but the complete workflow
migration and qualification set is incomplete. In particular, the ordinary
Apple and firmware CI workflow dispatches ended in no-job `startup_failure`;
Windows, Pi, Home Assistant, API and website workflow evidence is still
pending. The block does not permit Codex or GitHub-hosted runners to
substitute for a platform build.
