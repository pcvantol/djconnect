# Trusted AI Actor Report

Status: qualified for bounded canonical-repository delivery validation
Decision: `TRUSTED_AI_ACTOR_QUALIFIED`

## Evidence

The GitHub App was manually registered and installed. The personal CLI token
remains unsuitable for App discovery, so objective validation used a short-
lived installation token generated in GitHub Actions.

## Prepared Configuration

- App name: `DJConnect Trusted Delivery`
- Owner: `pcvantol`
- App ID: `4281587`
- Client ID: `Iv23liUAB5abfNYj04Z6`
- Installation ID: `146140223`
- Installation: selected active DJConnect repositories only
- Permission contract: `software_assurance/trusted_delivery/github-app-policy.json`
- Manual procedure: `DJCONNECT_TRUSTED_DELIVERY_APP_SETUP.md`

No private key, installation token, webhook secret or repository secret was
created, stored in Git, or exposed.

## Validation Evidence

- GitHub Actions secret presence was confirmed without reading its content.
- The App ID and Installation ID were supplied as non-secret configuration.
- Run `29206706003` passed using SHA-pinned
  `actions/create-github-app-token`.
- The App token read checks, pushed an app-owned harmless validation branch,
  created a pull request, then closed the pull request and deleted the branch.
- No production change was merged and no token value appeared in logs.

The test proves bounded contents, pull-request and checks access for
`pcvantol/djconnect`. Prompt 3 must still read back installation selection and
effective permissions across every active repository before platform-wide
Trusted Delivery rollout.
