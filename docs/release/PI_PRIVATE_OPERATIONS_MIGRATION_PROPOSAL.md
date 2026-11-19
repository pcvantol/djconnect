# Pi private operations migration proposal

Status: PROPOSED. This proposal does not authorize deployment or amend an
existing operational manifest. Existing approved manifests and their evidence
remain immutable. The existing Pi client deployment contract remains binding
until a separately reviewed and qualified successor is available.

## Problem

The Pi consumer currently verifies that its workflow run, the consumer checkout
and the source repository all have the same repository identity. That condition
cannot describe a protected execution workflow in the separate private Pi
operations repository. Moving private runner credentials into the public
source repository, fabricating GitHub environment variables, or treating a
successful runner readiness check as deployment authority would weaken the
existing boundary.

## Required successor contract

A successor must bind both identities independently and explicitly:

- The Pi source repository has stable GitHub repository ID `1267248532`.
  Its authorized organization name after transfer is
  `djconnect-music-dj/djconnect-pi`. An exact protected source commit supplies
  the consumer code and is separately bound to the approved artifact and
  operational manifest.
- The private execution repository has stable GitHub repository ID
  `1458225033` and name `djconnect-music-dj/djconnect-pi-operations`. Its exact
  protected commit and an allowlisted phase-specific workflow path are bound
  independently from the Pi consumer commit.
- Verify the actual GitHub Actions run by API against the execution repository
  ID, name, protected main ref, exact execution commit, workflow path, event,
  run and attempt, and the authorized actor. Check out the separately approved
  consumer commit and verify its Git object and repository ID. Neither a caller
  input nor an environment-variable override may substitute for either identity.
- Bind the resulting deployment and smoke receipts to both identities and both
  revisions, the original approved manifest and artifact, device instance,
  profile, inventory digest and deployment run. A smoke run must join to the
  successful deployment from the same qualified private execution context.
- Preserve the existing instance-specific host-key and hardware checks,
  configuration custody, approval freshness, one-attempt mutation guard,
  readiness, installer, recovery and read-only smoke requirements. Old
  manifests and source-only runs keep their original meanings and cannot be
  silently reinterpreted as private-execution evidence.
- Version and qualify the manifest and consumer schemas before adoption. Reject
  wrong or missing repository IDs, wrong repository names, mutable or mismatched
  revisions, wrong workflow or actor, cross-instance and cross-run substitutions,
  stale approvals and reruns before any remote mutation. Keep source tests,
  runner readiness, private workflow qualification, deployment and physical
  acceptance as distinct evidence.

This proposal grants no runner, secret, target or operational authorization.
The qualified successor implementation, separately approved exact manifest and
verified private runner configuration are prerequisites to use the route.
