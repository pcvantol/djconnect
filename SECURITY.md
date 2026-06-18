# DJConnect Security Policy

## Reporting A Vulnerability

Please report security vulnerabilities privately by email:

```text
security@djconnect.dev
```

Do not open a public GitHub issue for suspected security vulnerabilities.
Private reporting gives the maintainer time to investigate and prepare a fix
before details are widely visible.

Useful report details include:

- Affected repository, version and component.
- A clear description of the issue and impact.
- Steps to reproduce or a proof of concept, when safe to share.
- Any relevant logs, screenshots or configuration details with secrets removed.
- Whether you believe tokens, credentials, local network access or user data may
  be exposed.

Please do not include real Spotify refresh tokens, Home Assistant tokens,
device bearer tokens, WiFi passwords or other secrets in the report.

## What To Expect

The project maintainer will review security reports and respond as soon as
practical. DJConnect is a small community project, so response times may vary,
but reports sent to `security@djconnect.dev` are the preferred path and will be
handled with care.

When a vulnerability is confirmed, the maintainer will work on an appropriate
fix, document the user impact where needed and publish release notes once the
fix is available.

## Supported Versions

DJConnect follows the current `3.1.x` integration line. Security fixes are
normally released in the latest `3.1.x` version through HACS. Users should
upgrade to the latest release before reporting an issue that may already be
fixed.

## Security Scope

In scope for this repository:

- Home Assistant custom integration code under `custom_components/djconnect/`.
- Pairing, bearer-token validation and DJConnect HTTP endpoints.
- Spotify OAuth handling and refresh-token storage inside Home Assistant.
- Diagnostics/logging redaction for tokens, passwords and secrets.
- Release/documentation workflows that could expose credentials or private
  artifacts.

Out of scope for this repository:

- Vulnerabilities in Spotify, Home Assistant, HACS, GitHub or third-party
  services themselves.
- Firmware, Apple client, Raspberry Pi client or website issues that belong in
  a separate DJConnect repository. You may still email
  `security@djconnect.dev`, and the report can be routed to the right repo.

## Safe Research Guidelines

Please avoid actions that could harm users or services:

- Do not access, modify or delete data that is not yours.
- Do not attempt denial-of-service attacks.
- Do not publicly disclose a vulnerability before a fix or mitigation is
  available.
- Do not exfiltrate tokens, passwords, audio, local-network data or private
  configuration.
- Use your own Home Assistant instance, DJConnect device/client and Spotify
  account when testing.

Good-faith security research that follows these guidelines is welcome.
