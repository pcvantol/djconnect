# DJConnect Trusted Delivery GitHub App Setup

Decision before registration: `AWAITING_GITHUB_APP_REGISTRATION`.

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
