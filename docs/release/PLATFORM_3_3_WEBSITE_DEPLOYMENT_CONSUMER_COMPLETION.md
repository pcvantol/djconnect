# Platform Release 3.3 — Website Deployment Consumer Implementation

Date: 2026-07-14
Decision: `WEBSITE_DEPLOYMENT_CONSUMER_IMPLEMENTED_OPERATIONAL_QUALIFICATION_BLOCKED`

## Executive summary

The Website now implements the canonical three-workflow deployment-consumer
pattern. The artifact producer, Cloudflare Pages deployment consumer and
post-deployment smoke consumer are separated. The implementation is locally
verified; no operational deployment was dispatched.

## Scope

- reusable implementation guidance:
  `DEPLOYMENT_CONSUMER_IMPLEMENTATION_TEMPLATE.md`;
- website artifact workflow:
  `djconnect-website/.github/workflows/website-release-artifact.yml`;
- manifest-bound Website deployment workflow:
  `djconnect-website/.github/workflows/deploy-pages.yml`;
- separate Website smoke workflow:
  `djconnect-website/.github/workflows/website-post-deployment-smoke.yml`.

## Verification and evidence

- all Website workflow YAML files parse successfully;
- mutable GitHub Action reference scan passed;
- Website `npm test` passed: 66 tests, including five-language rendering and
  the release-workflow contract assertions;
- `git diff --check` passed for the Website implementation.

## Known issues and readiness

Operational qualification is blocked, before mutation, by the absence of an
approved current-main release manifest, qualifying artifact evidence and
explicit Internal Release authorization. No production Pages deployment,
artifact publication or smoke dispatch occurred.

## Assessment

The implementation follows the frozen release architecture: artifact
production, deployment and smoke remain separate responsibilities; no new
platform subsystem or contract has been introduced. No Verification Platform
or Meta Engineering change is required.

## Next phase

Do not dispatch these workflows automatically. The next authorized work is the
private-network deployment consumer for Home Assistant, Raspberry Pi and ESP32
or an explicitly authorized Website operational qualification against a future
approved manifest.
