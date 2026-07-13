# DJConnect Trusted Delivery GitHub App Setup

Decision: `CONFIGURED_FOR_CENTRAL_OWNER_AUTHORIZATION`.

Create a private GitHub App owned by `pcvantol`; do not publish it to the
Marketplace and do not make it installable by arbitrary accounts.

1. Open GitHub **Account Settings** → **Developer settings** → **GitHub Apps** → **New GitHub App**.
2. Enter name: `DJConnect Trusted Delivery`.
3. Enter description: `Least-privilege trusted delivery actor for governed DJConnect branch, pull-request, qualification and auto-merge operations.`
4. Homepage URL: `https://github.com/pcvantol/djconnect`.
5. Disable user authorization. Do not supply an OAuth callback URL. Disable device flow.
6. Disable webhooks; no initial webhook event is required.
7. Set repository permissions exactly: Metadata **Read-only**; Contents **Read and write**; Pull requests **Read and write**; Checks **Read-only**; Commit statuses **Read and write**; Actions **Read-only**. Commit-status write access is used only by the central Owner Authorization workflow to publish the exact-SHA `Owner Authorization` decision after technical Trusted Delivery qualification has passed.
8. Do not grant Administration, Members, Secrets, Environments, Repository hooks, Packages, Deployments, Security events, Actions write or Workflows write.
9. Create the app and record its non-secret App ID.
10. Generate one private key and provision it only through the approved secret-management path. Never paste, commit or report the PEM.
11. Install the app only on selected repositories: `djconnect`, `djconnect-api`, `djconnect-app`, `djconnect-app-releases`, `djconnect-esp32`, `djconnect-firmware`, `djconnect-pi`, `djconnect-pi-releases`, `djconnect-website`, `djconnect-windows`.
12. Record the non-secret installation ID. Provision these names only after secure key handling is confirmed: `DJCONNECT_TRUSTED_DELIVERY_APP_ID`, `DJCONNECT_TRUSTED_DELIVERY_PRIVATE_KEY`, `DJCONNECT_TRUSTED_DELIVERY_INSTALLATION_ID`.

Return only the App ID, Installation ID, and confirmation that the private key
was securely provisioned. Do not return a private key, installation token,
webhook secret or repository secret.

## Central Owner Authorization operation

`pcvantol/djconnect/.github/workflows/owner-authorization.yml` is the
canonical authorization entry point. For a HIGH_RISK consumer candidate that
cannot yet dispatch its own workflow from `main`, the owner dispatches this
root workflow with the exact `repository`, `pr_number`, `candidate_sha` and
target `branch`.

The workflow accepts only repositories selected for this GitHub App
installation. It then mints a short-lived installation token scoped to the one
requested repository; the token is neither exposed nor persisted. Before it
can publish the `Owner Authorization` status, it verifies all of the following
against live GitHub data:

- the PR still targets the stated branch and its current head is the supplied
  full SHA;
- the existing `Owner Authorization` status is the expected HIGH_RISK request;
- `Trusted Delivery qualification / Qualify trusted delivery` is completed and
  successful in the candidate's GitHub status-check rollup; and
- the dispatch actor is the configured owner.

The only cross-repository write is the successful `Owner Authorization`
commit status on that exact SHA. The workflow produces an authorization
evidence artifact. It does not merge, tag, publish, deploy, build, or modify
repository contents.

After a consumer's thin dispatcher has merged to its own `main`, that
dispatcher may invoke the same reusable workflow for its own repository. It
cannot target another repository; the caller-scoped token remains restricted to
the caller repository.
