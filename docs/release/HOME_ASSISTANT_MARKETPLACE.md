# DJConnect in Home Assistant Marketplace

Home Assistant 2026.11 includes the Marketplace under **Settings → Marketplace**.
Earlier supported Home Assistant versions use HACS. Both read the same catalog
and repository metadata. The existing My Home Assistant link opens the correct
store for each version. DJConnect is a community integration with the
`djconnect` domain. [Home Assistant Marketplace documentation](https://www.home-assistant.io/integrations/marketplace/)

## Qualify and publish the integration release

1. Select the protected Core `main` commit for the public release. Confirm that
   its version agrees across the integration manifest, constants, changelog and
   release tag. Retain successful, exact-commit links for the existing HACS job
   without ignored checks and the hassfest job in Core CI. Complete the standard
   Core release qualification before publishing.
2. Publish a full GitHub integration release from that commit in
   `pcvantol/djconnect`. Use the existing integration tag convention
   (`v4.0.0` for version `4.0.0`). The store uses the tagged source tree, with
   `hacs.json` at its root and `custom_components/djconnect/` inside it. Include
   public release notes and any upgrade instructions.
3. Verify the published integration release is the version the store offers by
   default. Developer onboarding packages share this repository's releases page,
   and its GitHub latest release has pointed to `onboarding-v4.0.0`. Verify the
   offered release as well as GitHub's latest-release record after any onboarding
   publication. Keep internal HA artifacts and external TestFlight qualification
   separate from public Marketplace release evidence.
4. On an isolated Home Assistant 2026.11 instance, open the repository link and
   add it as a custom integration repository. Confirm the offered version,
   install it, check the DJConnect brand and setup wizard, and verify an update
   from the supported older integration release preserves its configuration.
   Retain the observed release tag and installed version with the smoke evidence.

[Marketplace release and update behavior](https://contributors.home-assistant.io/marketplace/guides/releases/)

## Submit to the shared catalog

From a personal maintainer fork of `hacs/default`, branch from `master` and add
`"pcvantol/djconnect"` alphabetically to the JSON list in `integration`. Submit
the completed catalog PR template with the full integration release URL, a
passing HACS run without ignored checks, and a passing hassfest run. Check the
listing after acceptance and catalog refresh. The repository link is the
installation entry point while catalog review is pending.

[Official catalog submission guide](https://contributors.home-assistant.io/marketplace/guides/catalog/)
