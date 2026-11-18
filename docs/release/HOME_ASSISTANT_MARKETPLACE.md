# Home Assistant Marketplace release preparation

This guide describes preparation and verification for a future public DJConnect
integration release. It does not declare a release ready, authorize publication,
or replace the existing Core release gates.

Home Assistant Marketplace and HACS use the shared community catalog. A user
can also add a repository by link before catalog acceptance. See the official
[Marketplace catalog guide](https://contributors.home-assistant.io/marketplace/guides/catalog/)
and [Marketplace documentation](https://www.home-assistant.io/integrations/marketplace/).
The current repository is `djconnect-music-dj/djconnect`.

## Prepare the candidate

1. Select the exact protected Core `main` commit for the intended release. Check
   the integration manifest version, release tag and release notes agree. Check
   the repository's current Home Assistant compatibility requirements; do not
   change the minimum version merely to prepare a Marketplace listing.
2. Review the exact-commit Core CI, including the applicable HACS and hassfest
   checks, and follow the existing release qualification and approval policy.
   An individual green check is not release authorization. Record any deferred
   qualification as deferred rather than representing it as passed.
3. Verify the exact candidate's durable qualification evidence in accordance
   with [Artifact Release Evidence Policy](ARTIFACT_RELEASE_EVIDENCE_POLICY.md).
   Missing or stale evidence leaves that qualification not ready.
4. Independently verify the intended GitHub release target and the version the
   store would offer. A versioned Marketplace offer uses a published GitHub
   release; a tag alone is insufficient. When no release exists, Marketplace
   may instead offer the latest default-branch commit. Internal `internal-ha-<main-sha>` prereleases and onboarding
   releases serve different purposes and must not be mistaken for the public
   integration release. See [Releases and updates](https://contributors.home-assistant.io/marketplace/guides/releases/).

The existing `home-assistant-release-artifact.yml` produces an immutable
internal prerelease artifact. It is not, by itself, a public Marketplace release
or authorization to publish one. Use the separately approved public release
procedure when one is established; this document does not define a new one.

## Verify before catalog submission

On an isolated, supported Home Assistant instance, verify the repository link,
offered release, installation, existing-configuration preservation and setup
flow. Record the actual Home Assistant version, release tag, installed version,
candidate SHA and outcome. Do not infer a live installation or catalog listing
from source, CI or an internal artifact alone.

For a future shared-catalog submission, follow the current official
[catalog submission guide](https://contributors.home-assistant.io/marketplace/guides/catalog/)
and check the current `hacs/default` instructions and validation requirements.
Confirm the repository identity and published release at submission time. Until
catalog acceptance is observed, do not claim that DJConnect is listed.
